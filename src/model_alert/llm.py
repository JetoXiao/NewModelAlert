from __future__ import annotations

import json

import httpx

from .settings import Settings


class LlmSummarizer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def summarize_event(self, event, sources, heat, score: int) -> str | None:
        if not self.settings.llm_enabled:
            return None

        facts = [
            {
                "title": row["title"],
                "summary": row["summary"][:1000],
                "source_name": row["source_name"],
                "source_url": row["source_url"],
                "credibility": row["source_credibility"],
            }
            for row in sources[:6]
        ]
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是大模型情报分析助手。只基于用户提供的来源事实写中文摘要，"
                        "不能编造 benchmark、价格、日期或评价。不能确认的信息必须标注为未确认。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "event": {
                                "provider": event["provider_name"],
                                "model_hint": event["model_hint"],
                                "event_type": event["event_type"],
                                "score": score,
                            },
                            "influential_mentions": heat.influential_mentions,
                            "sources": facts,
                            "task": (
                                "生成不超过350字的中文推送正文，只关注新模型发布本身，包含："
                                "事件一句话结论、具体发布内容、相对上一代/旧版本的变化、"
                                "我需要关注的行动建议。不要写普通社区讨论、GitHub 搜索量、"
                                "Hacker News 热度、开发者讨论量或媒体转述。"
                            ),
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0.2,
        }

        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            print(f"[warn] llm summarize failed: {exc}")
            return None
