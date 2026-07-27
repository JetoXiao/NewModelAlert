from __future__ import annotations

from datetime import datetime, timezone

from .classifier import classify_item
from .config import Registry
from .fetchers import Fetcher
from .heat import HeatCollector, is_major_supplement
from .llm import LlmSummarizer
from .messages import build_main_message, build_supplement_message
from .notifier import WeComNotifier
from .scoring import event_score
from .settings import Settings
from .store import Store


BOOTSTRAP_DONE_KEY = "bootstrap_done_at"
SCAN_SUCCESS_KEY = "last_successful_scan_at"


class MonitorRunner:
    def __init__(self, settings: Settings, registry: Registry, store: Store) -> None:
        self.settings = settings
        self.registry = registry
        self.store = store
        self.notifier = WeComNotifier(settings)
        self.summarizer = LlmSummarizer(settings)

    def run_once(self) -> None:
        if not self.settings.wechat_webhook_url:
            print("[warn] WECHAT_WEBHOOK_URL is empty; notifications will be printed only")
        bootstrap = self.store.get_kv(BOOTSTRAP_DONE_KEY) is None and not self.settings.bootstrap_notify
        last_successful_scan = self.store.get_kv(SCAN_SUCCESS_KEY)
        catchup_baseline = (
            not bootstrap
            and not self.settings.bootstrap_notify
            and self._scan_gap_exceeds_threshold(last_successful_scan)
        )
        if bootstrap:
            print("[info] first run baseline mode enabled; historical items will not be pushed")
        elif catchup_baseline:
            print("[warn] long scan gap detected; current scan will refresh baseline without pushing historical backlog")

        fetcher = Fetcher(self.settings)
        signals_seen = 0
        try:
            for provider in self.registry.providers:
                items = fetcher.fetch_provider(provider)
                for item in items:
                    is_new_item = self.store.add_source_item(item)
                    if not is_new_item:
                        continue
                    signal = classify_item(provider, item, self.registry.event_keywords)
                    if signal is None:
                        continue
                    if signal.event_type != "release":
                        continue
                    self.store.upsert_signal(signal, bootstrap=bootstrap or catchup_baseline)
                    signals_seen += 1
        finally:
            fetcher.close()

        expired = self.store.expire_stale_pending(self.settings.pending_event_max_age_hours)
        if expired:
            print(f"[info] expired stale pending events={expired}")

        self.store.set_kv(SCAN_SUCCESS_KEY, datetime.now(timezone.utc).isoformat())

        if bootstrap or catchup_baseline:
            self.store.set_kv(BOOTSTRAP_DONE_KEY, datetime.now(timezone.utc).isoformat())
            print(f"[info] baseline refreshed; signals={signals_seen}")
            return

        print(f"[info] scan complete; new_signals={signals_seen}")
        self._send_ready_main_notifications()
        self._send_major_supplements()

    def _scan_gap_exceeds_threshold(self, last_successful_scan: str | None) -> bool:
        if not last_successful_scan:
            return True
        try:
            last = datetime.fromisoformat(last_successful_scan.replace("Z", "+00:00"))
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
        except ValueError:
            return True
        gap = datetime.now(timezone.utc) - last.astimezone(timezone.utc)
        return gap.total_seconds() >= self.settings.catchup_baseline_after_hours * 3600

    def _send_ready_main_notifications(self) -> None:
        ready = self.store.pending_events_ready(
            self.settings.event_settle_minutes,
            self.settings.pending_event_max_age_hours,
        )
        if not ready:
            print("[info] no settled pending event ready for notification")
            return

        heat_collector = HeatCollector(self.settings, self.registry.influential_people)
        try:
            for event in ready:
                if event["event_type"] != "release":
                    continue
                sources = self.store.get_event_sources(event["signature"])
                heat = heat_collector.collect(event["provider_name"], event["model_hint"])
                score = event_score(event, len(sources), heat)
                llm_summary = self.summarizer.summarize_event(event, sources, heat, score)
                title, markdown = build_main_message(event, sources, heat, score, llm_summary)
                self.notifier.send_markdown(title, markdown)
                self.store.mark_main_notified(event["signature"], heat)
                print(f"[info] main notification sent signature={event['signature']} score={score}")
        finally:
            heat_collector.close()

    def _send_major_supplements(self) -> None:
        events = self.store.notified_events_for_supplement_scan(hours=96)
        if not events:
            return

        heat_collector = HeatCollector(self.settings, self.registry.influential_people)
        try:
            for event in events:
                heat = heat_collector.collect(event["provider_name"], event["model_hint"])
                should_send, reason = is_major_supplement(event, heat)
                if not should_send:
                    continue
                sources = self.store.get_event_sources(event["signature"])
                title, markdown = build_supplement_message(event, sources, heat, reason)
                self.notifier.send_markdown(title, markdown)
                self.store.mark_supplement_notified(event["signature"], heat)
                print(f"[info] supplement notification sent signature={event['signature']} reason={reason}")
        finally:
            heat_collector.close()
