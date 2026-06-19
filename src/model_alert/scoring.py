from __future__ import annotations

import sqlite3

from .models import HeatMetrics


EVENT_BASE = {
    "release": 88,
    "deprecation": 84,
    "update": 76,
}

PRIORITY_BONUS = {
    "P0": 6,
    "P1": 3,
    "P2": 1,
}


def event_score(event: sqlite3.Row, source_count: int, heat: HeatMetrics) -> int:
    base = EVENT_BASE.get(event["event_type"], 70)
    confidence = int(event["confidence"] or 0)
    source_bonus = min(source_count * 3, 12)
    heat_bonus = min(heat.score // 8, 10)
    priority_bonus = PRIORITY_BONUS.get(event["provider_priority"], 0)
    score = base * 0.45 + confidence * 0.35 + source_bonus + heat_bonus + priority_bonus
    return max(0, min(100, round(score)))


def rating_label(score: int) -> str:
    if score >= 90:
        return "强烈关注"
    if score >= 80:
        return "值得优先关注"
    if score >= 70:
        return "建议关注"
    if score >= 55:
        return "一般关注"
    return "低优先级"
