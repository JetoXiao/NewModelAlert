from __future__ import annotations

import argparse
import time

from apscheduler.schedulers.blocking import BlockingScheduler

from .config import load_registry
from .runner import MonitorRunner
from .settings import Settings
from .store import Store
from .notifier import WeComNotifier


def build_runner() -> MonitorRunner:
    settings = Settings()
    registry = load_registry(settings.registry_path)
    store = Store(settings.db_path)
    return MonitorRunner(settings, registry, store)


def run_once() -> None:
    runner = build_runner()
    runner.run_once()


def send_test() -> None:
    settings = Settings()
    notifier = WeComNotifier(settings)
    notifier.send_markdown(
        "New Model Alert 测试",
        "**New Model Alert 测试消息**\n\n企业微信机器人已连通。后续只有模型发布、更新、下架或重大补充消息才会推送。",
    )


def show_registry() -> None:
    settings = Settings()
    registry = load_registry(settings.registry_path)
    for provider in registry.providers:
        print(
            f"{provider.priority} {provider.id} {provider.name} "
            f"sources={len(provider.sources)} families={','.join(provider.model_families)}"
        )


def run_scheduler() -> None:
    settings = Settings()
    registry = load_registry(settings.registry_path)
    store = Store(settings.db_path)
    runner = MonitorRunner(settings, registry, store)

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        runner.run_once,
        "interval",
        minutes=settings.poll_interval_minutes,
        id="model-alert-scan",
        max_instances=1,
        coalesce=True,
        next_run_time=None,
    )
    print(f"[info] scheduler started; interval={settings.poll_interval_minutes} minutes")
    runner.run_once()
    scheduler.start()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", default="run", choices=["run", "once", "test", "registry"])
    parser.add_argument("--once", action="store_true", help="Run one scan and exit.")
    args = parser.parse_args()

    if args.once or args.command == "once":
        run_once()
    elif args.command == "test":
        send_test()
    elif args.command == "registry":
        show_registry()
    else:
        try:
            run_scheduler()
        except KeyboardInterrupt:
            print("[info] stopped")
            time.sleep(0.1)


if __name__ == "__main__":
    main()
