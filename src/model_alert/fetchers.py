from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

import feedparser
import httpx
from bs4 import BeautifulSoup

from .config import Provider, Source
from .models import CandidateItem
from .settings import Settings
from .text import clean_text, short_text, stable_hash


class Fetcher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = httpx.Client(
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": settings.user_agent},
        )
        self.insecure_client = httpx.Client(
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
            verify=False,
            headers={"User-Agent": settings.user_agent},
        )

    def close(self) -> None:
        self.client.close()
        self.insecure_client.close()

    def _get(self, url: str, **kwargs) -> httpx.Response:
        try:
            response = self.client.get(url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.TransportError as exc:
            if "SSL" not in str(exc) and "EOF" not in str(exc):
                raise
            response = self.insecure_client.get(url, **kwargs)
            response.raise_for_status()
            return response

    def fetch_provider(self, provider: Provider) -> list[CandidateItem]:
        items: list[CandidateItem] = []
        for source in provider.sources:
            try:
                if source.type == "rss" and source.url:
                    items.extend(self._fetch_rss(provider, source))
                elif source.type == "webpage" and source.url:
                    items.extend(self._fetch_webpage(provider, source))
                elif source.type == "github" and source.repo:
                    items.extend(self._fetch_github(provider, source))
            except Exception as exc:
                print(f"[warn] fetch failed provider={provider.id} source={source.name}: {exc}")
        return items

    def _candidate(
        self,
        provider: Provider,
        source: Source,
        title: str,
        url: str,
        summary: str,
        published_at: datetime | None,
    ) -> CandidateItem:
        title = clean_text(title) or source.name
        summary = short_text(summary, 1200)
        url = url or source.url or ""
        content_hash = stable_hash(f"{provider.id}|{source.name}|{title}|{url}|{summary[:200]}")
        return CandidateItem(
            provider_id=provider.id,
            provider_name=provider.name,
            provider_priority=provider.priority,
            source_name=source.name,
            source_type=source.type,
            source_url=source.url or url,
            source_credibility=source.credibility,
            title=title,
            url=url,
            summary=summary,
            content_hash=content_hash,
            published_at=published_at,
        )

    def _fetch_rss(self, provider: Provider, source: Source) -> list[CandidateItem]:
        response = self._get(source.url or "")
        feed = feedparser.parse(response.content)
        items: list[CandidateItem] = []
        for entry in feed.entries[:20]:
            published_at = _parse_rss_dt(
                entry.get("published")
                or entry.get("updated")
                or entry.get("created")
            )
            items.append(
                self._candidate(
                    provider,
                    source,
                    title=entry.get("title", ""),
                    url=entry.get("link", source.url or ""),
                    summary=entry.get("summary", "") or entry.get("description", ""),
                    published_at=published_at,
                )
            )
        return items

    def _fetch_webpage(self, provider: Provider, source: Source) -> list[CandidateItem]:
        response = self._get(source.url or "")
        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()

        candidates: list[CandidateItem] = []
        seen_urls: set[str] = set()
        for heading in soup.find_all(["h1", "h2", "h3"])[:25]:
            title = clean_text(heading.get_text(" "))
            if len(title) < 4:
                continue
            chunks = [title]
            for sibling in heading.find_next_siblings(limit=4):
                if sibling.name in {"h1", "h2", "h3"}:
                    break
                text = clean_text(sibling.get_text(" "))
                if text:
                    chunks.append(text)
            anchor = heading.find("a") or heading.find_parent("a")
            href = anchor.get("href") if anchor else None
            url = urljoin(source.url or "", href) if href else source.url or ""
            key = f"{title}|{url}"
            if key in seen_urls:
                continue
            seen_urls.add(key)
            candidates.append(
                self._candidate(
                    provider,
                    source,
                    title=title,
                    url=url,
                    summary=" ".join(chunks),
                    published_at=None,
                )
            )

        if not candidates:
            title = clean_text(soup.title.get_text(" ")) if soup.title else source.name
            body = short_text(clean_text(soup.get_text(" ")), 1600)
            candidates.append(
                self._candidate(
                    provider,
                    source,
                    title=title,
                    url=source.url or "",
                    summary=body,
                    published_at=None,
                )
            )
        return candidates[:20]

    def _fetch_github(self, provider: Provider, source: Source) -> list[CandidateItem]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        url = f"https://api.github.com/repos/{source.repo}/releases"
        response = self._get(url, headers=headers)
        items: list[CandidateItem] = []
        for release in response.json()[:10]:
            published_at = _parse_iso_dt(release.get("published_at"))
            items.append(
                self._candidate(
                    provider,
                    source,
                    title=release.get("name") or release.get("tag_name") or source.name,
                    url=release.get("html_url") or f"https://github.com/{source.repo}/releases",
                    summary=release.get("body") or "",
                    published_at=published_at,
                )
            )
        return items


def _parse_rss_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _parse_iso_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None
