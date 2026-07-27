from __future__ import annotations

import sqlite3

from .models import HeatMetrics
from .scoring import rating_label
from .text import short_text


EVENT_LABELS = {
    "release": "新模型发布",
    "update": "模型更新",
    "deprecation": "模型下架/弃用",
}


def build_main_message(
    event: sqlite3.Row,
    sources: list[sqlite3.Row],
    heat: HeatMetrics,
    score: int,
    llm_summary: str | None,
) -> tuple[str, str]:
    event_label = EVENT_LABELS.get(event["event_type"], event["event_type"])
    title = f"[{event_label}] {event['provider_name']} / {event['model_hint']}"
    source_lines = []
    for row in sources[:5]:
        source_lines.append(f"> [{row['source_name']}]({row['source_url']})：{short_text(row['title'], 80)}")

    if llm_summary:
        analysis = llm_summary
    else:
        first = sources[0] if sources else None
        analysis = (
            f"{event['provider_name']} 出现{event_label}信号，模型线索为 "
            f"`{event['model_hint']}`。"
        )
        if first:
            analysis += f"\n\n发布内容：{short_text(first['summary'], 420)}"

    influence_line = "重要人物提及：暂无明确命中。"
    if heat.influential_mentions:
        influence_line = "重要人物提及：" + "、".join(sorted(set(heat.influential_mentions))) + "。"

    markdown = f"""**{title}**

评分：**{score}/100（{rating_label(score)}）**
可信度：{event['confidence']}/100；来源数：{len(sources)}

{analysis}

{influence_line}

处理策略：本事件已作为主消息推送。后续只在超高影响力人物明确点名该模型时补充推送；普通社区讨论、GitHub 搜索量、Hacker News 热度和媒体转述不会触发补推。

来源：
{chr(10).join(source_lines)}
"""
    return title, markdown


def build_supplement_message(
    event: sqlite3.Row,
    sources: list[sqlite3.Row],
    heat: HeatMetrics,
    reason: str,
) -> tuple[str, str]:
    title = f"[补充更新] {event['provider_name']} / {event['model_hint']}"
    source_lines = []
    for row in sources[:3]:
        source_lines.append(f"> [{row['source_name']}]({row['source_url']})：{short_text(row['title'], 80)}")

    markdown = f"""**{title}**

补充原因：**{reason}**

这条补充只因为超高影响力人物明确点名该模型而发送，不会因为社区讨论量或市场热度发送。

来源：
{chr(10).join(source_lines)}
"""
    return title, markdown
