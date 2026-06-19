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
            analysis += f"\n\n具体内容：{short_text(first['summary'], 420)}"

    heat_line = (
        f"市场热度：{heat.score}/100；Hacker News 相关信号 {heat.hn_hits} 条，"
        f"GitHub 相关仓库/讨论约 {heat.github_hits} 条，相关仓库星标合计约 {heat.github_stars}。"
    )
    if heat.influential_mentions:
        heat_line += " 重要人物提及：" + "、".join(sorted(set(heat.influential_mentions))) + "。"

    markdown = f"""**{title}**

评分：**{score}/100（{rating_label(score)}）**
可信度：{event['confidence']}/100；来源数：{len(sources)}

{analysis}

{heat_line}

处理策略：本事件已作为主消息推送，后续只有重大进展、重要人物评价或热度显著上升才会补充推送。

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

当前市场热度：{heat.score}/100；Hacker News 相关信号 {heat.hn_hits} 条，GitHub 相关仓库/讨论约 {heat.github_hits} 条。

重要人物提及：{("、".join(sorted(set(heat.influential_mentions))) if heat.influential_mentions else "暂无明确命中")}

这条是对已推送模型事件的补充，不会重复发送主事件内容。

来源：
{chr(10).join(source_lines)}
"""
    return title, markdown
