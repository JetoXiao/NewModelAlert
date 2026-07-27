from __future__ import annotations

from urllib.parse import quote_plus

import httpx

from .config import InfluentialPerson
from .models import HeatMetrics
from .settings import Settings


class HeatCollector:
    def __init__(self, settings: Settings, people: list[InfluentialPerson]) -> None:
        self.settings = settings
        self.people = people
        self.client = httpx.Client(
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": settings.user_agent},
        )

    def close(self) -> None:
        self.client.close()

    def collect(self, provider_name: str, model_hint: str) -> HeatMetrics:
        metrics = HeatMetrics()
        self._detect_influential_mentions(provider_name, model_hint, metrics)
        return metrics

    def _detect_influential_mentions(self, provider_name: str, model_hint: str, metrics: HeatMetrics) -> None:
        # Only use discussion search to detect named mentions by very influential people.
        # Ordinary volume, GitHub counts, and HN activity must not trigger notifications.
        query = f'"{model_hint}" "{provider_name}"'
        haystacks: list[str] = []
        try:
            url = f"https://hn.algolia.com/api/v1/search?query={quote_plus(query)}&tags=comment,story&hitsPerPage=30"
            hits = self.client.get(url).json().get("hits", [])
            for hit in hits:
                haystacks.append(str(hit.get("title") or ""))
                haystacks.append(str(hit.get("comment_text") or ""))
                haystacks.append(str(hit.get("story_title") or ""))
        except Exception as exc:
            print(f"[warn] influence mention scan failed query={query}: {exc}")

        joined = " ".join(haystacks).lower()
        for person in self.people:
            if any(alias.lower() in joined for alias in person.aliases):
                metrics.influential_mentions.append(person.name)


def is_major_supplement(event_row, heat: HeatMetrics) -> tuple[bool, str]:
    if not heat.influential_mentions:
        return False, ""
    names = "、".join(sorted(set(heat.influential_mentions)))
    return True, f"重要人物明确提及：{names}"
