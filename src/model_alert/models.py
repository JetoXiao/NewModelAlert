from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class CandidateItem:
    provider_id: str
    provider_name: str
    provider_priority: str
    source_name: str
    source_type: str
    source_url: str
    source_credibility: str
    title: str
    url: str
    summary: str
    content_hash: str
    published_at: datetime | None
    discovered_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class EventSignal:
    item: CandidateItem
    event_type: str
    model_hint: str
    confidence: int
    matched_terms: list[str]
    is_official: bool
    signature: str


@dataclass
class HeatMetrics:
    hn_hits: int = 0
    hn_points: int = 0
    github_hits: int = 0
    github_stars: int = 0
    developer_discussions: int = 0
    influential_mentions: list[str] = field(default_factory=list)

    @property
    def score(self) -> int:
        raw = (
            self.hn_hits * 3
            + min(self.hn_points // 10, 20)
            + self.github_hits * 4
            + min(self.github_stars // 100, 25)
            + len(self.influential_mentions) * 15
        )
        return max(0, min(100, raw))
