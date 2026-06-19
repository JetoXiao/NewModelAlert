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
        query = f'"{model_hint}" "{provider_name}"'
        metrics = HeatMetrics()
        try:
            self._collect_hn(query, metrics)
        except Exception as exc:
            print(f"[warn] hn heat failed query={query}: {exc}")
        try:
            self._collect_github(model_hint, metrics)
        except Exception as exc:
            print(f"[warn] github heat failed query={query}: {exc}")
        self._detect_influential_mentions(query, metrics)
        metrics.developer_discussions = metrics.hn_hits + metrics.github_hits
        return metrics

    def _collect_hn(self, query: str, metrics: HeatMetrics) -> None:
        url = f"https://hn.algolia.com/api/v1/search?query={quote_plus(query)}&tags=story&hitsPerPage=10"
        data = self.client.get(url).json()
        hits = data.get("hits", [])
        metrics.hn_hits = len(hits)
        metrics.hn_points = sum(int(hit.get("points") or 0) for hit in hits)

    def _collect_github(self, model_hint: str, metrics: HeatMetrics) -> None:
        headers = {"Accept": "application/vnd.github+json"}
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        query = quote_plus(f"{model_hint} in:name,description,readme")
        url = f"https://api.github.com/search/repositories?q={query}&sort=updated&order=desc&per_page=10"
        response = self.client.get(url, headers=headers)
        response.raise_for_status()
        items = response.json().get("items", [])
        metrics.github_hits = int(response.json().get("total_count") or len(items))
        metrics.github_stars = sum(int(item.get("stargazers_count") or 0) for item in items)

    def _detect_influential_mentions(self, query: str, metrics: HeatMetrics) -> None:
        # Keep this deliberately conservative. Public search APIs for X/Weibo are not reliable
        # without paid or logged-in access, so this checks broad news/HN snippets only.
        haystacks: list[str] = []
        try:
            url = f"https://hn.algolia.com/api/v1/search?query={quote_plus(query)}&tags=comment&hitsPerPage=20"
            comments = self.client.get(url).json().get("hits", [])
            haystacks.extend(str(comment.get("comment_text") or "") for comment in comments)
        except Exception:
            pass

        joined = " ".join(haystacks).lower()
        for person in self.people:
            if any(alias.lower() in joined for alias in person.aliases):
                metrics.influential_mentions.append(person.name)


def is_major_supplement(event_row, heat: HeatMetrics) -> tuple[bool, str]:
    if heat.influential_mentions:
        names = "、".join(sorted(set(heat.influential_mentions)))
        return True, f"重要人物提及：{names}"

    prior_heat = int(event_row["heat_score_at_main"] or 0)
    if prior_heat >= 0 and heat.score >= max(65, prior_heat + 30):
        return True, f"市场热度明显上升：{prior_heat} -> {heat.score}"

    if heat.developer_discussions >= 30 and heat.score >= 55:
        return True, f"开发者讨论量较高：约 {heat.developer_discussions} 个公开讨论信号"

    return False, ""
