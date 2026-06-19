from __future__ import annotations

import httpx

from .settings import Settings


class WeComNotifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send_markdown(self, title: str, markdown: str) -> None:
        if self.settings.dry_run or not self.settings.wechat_webhook_url:
            print(f"\n[DRY RUN] {title}\n{markdown}\n")
            return

        payload = {
            "msgtype": "markdown",
            "markdown": {"content": markdown[:3900]},
        }
        response = httpx.post(self.settings.wechat_webhook_url, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("errcode") != 0:
            raise RuntimeError(f"WeCom send failed: {data}")


def truncate_for_wecom(value: str, limit: int = 3900) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 20].rstrip() + "\n\n...内容已截断"
