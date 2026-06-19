from __future__ import annotations

from .config import Provider
from .models import CandidateItem, EventSignal
from .text import clean_text, model_hint, normalize_signature_part, stable_hash


OFFICIAL_SOURCE_TYPES = {"rss", "webpage", "github"}
EVENT_WEIGHTS = {"release": 100, "update": 78, "deprecation": 95}
CREDIBILITY_WEIGHTS = {"S": 100, "A": 82, "B": 62, "C": 35}
PRIORITY_WEIGHTS = {"P0": 12, "P1": 6, "P2": 2}


def classify_item(
    provider: Provider,
    item: CandidateItem,
    event_keywords: dict[str, list[str]],
) -> EventSignal | None:
    text = clean_text(f"{item.title} {item.summary}")
    text_lower = text.lower()
    best_event = ""
    best_terms: list[str] = []
    for event_type, terms in event_keywords.items():
        matched = [term for term in terms if term.lower() in text_lower]
        if matched and len(matched) > len(best_terms):
            best_event = event_type
            best_terms = matched

    family_hit = any(family.lower() in text_lower for family in provider.model_families)
    if not best_event and not family_hit:
        return None

    if not best_event:
        best_event = "update"

    is_official = item.source_type in OFFICIAL_SOURCE_TYPES and item.source_credibility in {"S", "A"}
    confidence = (
        EVENT_WEIGHTS.get(best_event, 60)
        + CREDIBILITY_WEIGHTS.get(item.source_credibility, 45)
        + PRIORITY_WEIGHTS.get(provider.priority, 0)
    ) // 2
    if family_hit:
        confidence += 8
    if is_official:
        confidence += 8
    confidence = max(0, min(100, confidence))

    hint = model_hint(text, provider.model_families, provider.name)
    title_part = normalize_signature_part(item.title)
    signature_base = f"{provider.id}:{best_event}:{normalize_signature_part(hint)}:{title_part}"
    if item.source_type == "webpage":
        signature_base = f"{signature_base}:{item.content_hash[:12]}"
    signature = stable_hash(signature_base)[:24]
    return EventSignal(
        item=item,
        event_type=best_event,
        model_hint=hint,
        confidence=confidence,
        matched_terms=best_terms,
        is_official=is_official,
        signature=signature,
    )
