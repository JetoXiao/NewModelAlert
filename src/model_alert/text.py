from __future__ import annotations

import hashlib
import re
import warnings
from html import unescape

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning


WHITESPACE_RE = re.compile(r"\s+")
SPECIFIC_MODELISH_RE = re.compile(
    r"(?i)\b("
    r"gpt[-\s]?\d[\w.\-]*(?:[-\s]+(?:sol|turbo|mini|nano|pro|preview|audio|realtime|instruct|vision|thinking|reasoning|chat|omni|search)){0,4}|"
    r"o\d(?:[-\s]+(?:mini|pro|preview|high|reasoning)){0,4}|"
    r"claude(?:[-\s]+(?:opus|sonnet|haiku|fable|instant|[0-9][\w.\-]*)){1,4}|"
    r"gemini(?:[-\s]+(?:[0-9][\w.\-]*|ultra|pro|flash|flash-lite|nano|exp|live|thinking|experimental)){1,4}|"
    r"llama(?:[-\s]+(?:[0-9][\w.\-]*|guard|scout|maverick|herd|stack)){1,5}|"
    r"grok(?:[-\s]+(?:[0-9][\w.\-]*|beta|mini|code|vision)){1,4}|"
    r"deepseek(?:[-\s]+(?:v\d[\w.\-]*|r\d[\w.\-]*|[0-9][\w.\-]*|coder|vl|reasoner|chat|pro)){1,5}|"
    r"qwen(?:[-\s]+(?:[0-9][\w.\-]*|max|plus|turbo|coder|vl|omni|audio|image|chat|math)){1,5}|"
    r"glm(?:[-\s]+(?:[0-9][\w.\-]*|air|flash|plus|pro|zero|thinking)){1,5}|"
    r"kimi(?:[-\s]+(?:k\d[\w.\-]*|[0-9][\w.\-]*|latest|thinking|researcher|code|vl)){1,4}|"
    r"doubao(?:[-\s]+(?:[0-9][\w.\-]*|seed|pro|lite|vision)){1,5}|"
    r"ernie(?:[-\s]+(?:[0-9][\w.\-]*|bot|x1|turbo|speed|lite)){1,5}|"
    r"hunyuan(?:[-\s]+(?:[0-9][\w.\-]*|turbo|pro|lite|vision)){1,5}|"
    r"minimax(?:[-\s]+(?:[0-9][\w.\-]*|m1|text|vl|speech)){1,5}|"
    r"abab(?:[-\s]*[0-9][\w.\-]*)|"
    r"mistral(?:[-\s]+(?:[0-9][\w.\-]*|small|medium|large|nemo|pixtral)){1,5}|"
    r"mixtral(?:[-\s]+(?:[0-9][\w.\-]*|small|large)){1,5}|"
    r"codestral(?:[-\s]+(?:[0-9][\w.\-]*|embed|mamba)){0,4}|"
    r"command(?:[-\s]+(?:[0-9][\w.\-]*|a|r|r\+|light|nightly)){1,5}|"
    r"nova(?:[-\s]+(?:[0-9][\w.\-]*|micro|lite|pro|premier|reel|canvas)){1,5}|"
    r"titan(?:[-\s]+(?:[0-9][\w.\-]*|text|embed|image|premier|express|lite)){1,5}|"
    r"phi(?:[-\s]+(?:[0-9][\w.\-]*|mini|small|medium|silica)){1,5}|"
    r"nemotron(?:[-\s]+(?:[0-9][\w.\-]*|ultra|super|nano|reasoning)){1,5}|"
    r"jamba(?:[-\s]+(?:[0-9][\w.\-]*|mini|large)){1,5}|"
    r"yi(?:[-\s]+(?:[0-9][\w.\-]*|large|medium|vision|coder)){1,5}|"
    r"baichuan(?:[-\s]+(?:[0-9][\w.\-]*|turbo|air|m1)){1,5}|"
    r"spark(?:[-\s]+(?:[0-9][\w.\-]*|max|pro|lite|x1)){1,5}|"
    r"pangu(?:[-\s]+(?:[0-9][\w.\-]*|pro|ultra|nlp|cv)){1,5}"
    r")\b"
)
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
SPECIFIC_MODEL_MARKER_RE = re.compile(
    r"(?i)(\d|[-_\s](opus|sonnet|haiku|fable|instant|turbo|mini|nano|pro|preview|"
    r"flash|ultra|coder|vl|reasoner|reasoning|thinking|sol|max|plus|omni|audio|"
    r"vision|guard|maverick|scout|k\d|r\d|v\d|large|medium|small|lite|premier|"
    r"realtime|instruct|search|experimental|researcher|seed|x1|m1)\b)"
)


def clean_text(value: str) -> str:
    value = unescape(value or "")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", MarkupResemblesLocatorWarning)
        value = BeautifulSoup(value, "html.parser").get_text(" ")
    return WHITESPACE_RE.sub(" ", value).strip()


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def short_text(value: str, limit: int = 600) -> str:
    value = clean_text(value)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _compact_model_hint(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip(" -_.,:;，。")


def model_hint(text: str, families: list[str], provider_name: str) -> str:
    haystack = clean_text(text)
    for pattern in (SPECIFIC_MODELISH_RE, MODELISH_RE):
        match = pattern.search(haystack)
        if match:
            return _compact_model_hint(match.group(0))
    for family in families:
        if family.lower() in haystack.lower():
            return family
    return provider_name


def generic_model_hints(families: list[str], provider_name: str) -> set[str]:
    values = {provider_name, *families}
    return {clean_text(value).casefold() for value in values if clean_text(value)}


def is_specific_model_hint(hint: str, families: list[str], provider_name: str) -> bool:
    normalized = clean_text(hint).casefold()
    if not normalized or normalized in generic_model_hints(families, provider_name):
        return False
    return SPECIFIC_MODEL_MARKER_RE.search(normalized) is not None


def normalize_signature_part(value: str) -> str:
    value = clean_text(value).lower()
    value = re.sub(r"https?://\S+", "", value)
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    return value.strip("-")[:80]
