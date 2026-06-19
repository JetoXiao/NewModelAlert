from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Source:
    type: str
    name: str
    credibility: str
    url: str | None = None
    repo: str | None = None


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    region: str
    priority: str
    model_families: list[str]
    push_level: str
    sources: list[Source]


@dataclass(frozen=True)
class InfluentialPerson:
    id: str
    name: str
    aliases: list[str]
    weight: int


@dataclass(frozen=True)
class Registry:
    providers: list[Provider]
    influential_people: list[InfluentialPerson]
    event_keywords: dict[str, list[str]]


def load_registry(path: Path) -> Registry:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    providers = [
        Provider(
            id=item["id"],
            name=item["name"],
            region=item["region"],
            priority=item["priority"],
            model_families=list(item.get("model_families", [])),
            push_level=item.get("push_level", "normal"),
            sources=[
                Source(
                    type=source["type"],
                    name=source["name"],
                    credibility=source.get("credibility", "B"),
                    url=source.get("url"),
                    repo=source.get("repo"),
                )
                for source in item.get("sources", [])
            ],
        )
        for item in raw.get("providers", [])
    ]
    people = [
        InfluentialPerson(
            id=item["id"],
            name=item["name"],
            aliases=list(item.get("aliases", [])),
            weight=int(item.get("weight", 5)),
        )
        for item in raw.get("influential_people", [])
    ]
    return Registry(
        providers=providers,
        influential_people=people,
        event_keywords=raw.get("event_keywords", {}),
    )


def source_to_dict(source: Source) -> dict[str, Any]:
    return {
        "type": source.type,
        "name": source.name,
        "credibility": source.credibility,
        "url": source.url,
        "repo": source.repo,
    }
