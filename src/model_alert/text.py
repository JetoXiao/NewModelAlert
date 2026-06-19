from __future__ import annotations

import hashlib
import re
from html import unescape

from bs4 import BeautifulSoup


WHITESPACE_RE = re.compile(r"\s+")
MODELISH_RE = re.compile(
    r"(?i)\b("
    r"gpt[-\w.]*|o\d[-\w.]*|claude[-\w.]*|gemini[-\w.]*|llama[-\w.]*|"
    r"grok[-\w.]*|deepseek[-\w.]*|qwen[-\w.]*|glm[-\w.]*|kimi[-\w.]*|"
    r"doubao[-\w.]*|ernie[-\w.]*|hunyuan[-\w.]*|minimax[-\w.]*|"
    r"mistral[-\w.]*|mixtral[-\w.]*|codestral[-\w.]*|command[-\w.]*|"
    r"nova[-\w.]*|titan[-\w.]*|phi[-\w.]*|nemotron[-\w.]*|jamba[-\w.]*|"
    r"yi[-\w.]*|baichuan[-\w.]*|spark[-\w.]*|pangu[-\w.]*"
    r")\b|"
    r"(通义千问|智谱|文心|豆包|混元|百川|星火|盘古|阶跃|日日新)"
)


def clean_text(value: str) -> str:
    value = unescape(value or "")
    value = BeautifulSoup(value, "html.parser").get_text(" ")
    return WHITESPACE_RE.sub(" ", value).strip()


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def short_text(value: str, limit: int = 600) -> str:
    value = clean_text(value)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def model_hint(text: str, families: list[str], provider_name: str) -> str:
    haystack = clean_text(text)
    match = MODELISH_RE.search(haystack)
    if match:
        return match.group(0)
    for family in families:
        if family.lower() in haystack.lower():
            return family
    return provider_name


def normalize_signature_part(value: str) -> str:
    value = clean_text(value).lower()
    value = re.sub(r"https?://\S+", "", value)
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    return value.strip("-")[:80]
