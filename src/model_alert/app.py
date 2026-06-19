from __future__ import annotations

import argparse
import time

from apscheduler.schedulers.blocking import BlockingScheduler

from .config import load_registry
from .runner import MonitorRunner
from .settings import Settings
from .store import Store
from .notifier import WeComNotifier


def build_runner() -> MonitorRunner:
    settings = Settings()
    registry = load_registry(settings.registry_path)
    store = Store(settings.db_path)
    return MonitorRunner(settings, registry, store)


def run_once() -> None:
    runner = build_runner()
    runner.run_once()


def send_test() -> None:
    settings = Settings()
    notifier = WeComNotifier(settings)
    notifier.send_markdown(
        "New Model Alert 测试",
        "**New Model Alert 测试消息**\n\n企业微信机器人已连通。后续只有模型发布、更新、下架或重大补充消息才会推送。",
    )


def send_sample() -> None:
    settings = Settings()
    notifier = WeComNotifier(settings)
    markdown = """**[测试数据][新模型发布] Anthropic / claude-fable5**

> 这是人工构造的测试样例，不是真实新闻，不会写入监控数据库。

评分：**91/100（强烈关注）**
可信度：S（模拟官方公告）；来源数：3（模拟）
事件类型：新模型发布
推送策略：主消息，一次性汇总；后续仅在重大补充时推送。

一句话结论：Anthropic 模拟发布 `claude-fable5`，定位为 Claude Fable 系列的新一代长任务与创意写作模型，重点提升多轮规划、长上下文一致性和工具调用稳定性。

具体更新内容：
1. 长文本一致性增强：模拟支持更长上下文内的人设、术语和项目约束保持。
2. 代码与工具调用优化：模拟降低多步骤工具调用中的漏参、重复调用和格式漂移。
3. 创意写作能力提升：模拟加强叙事节奏、角色对话和风格迁移。
4. 企业使用改进：模拟增强安全策略遵循、结构化输出和批量任务稳定性。

相对上一代：
- 推理：中高幅提升，尤其是长任务拆解。
- 代码：小到中幅提升，主要体现在多文件修改和测试修复。
- 写作：明显提升，适合长篇内容、角色设定和品牌语气控制。
- 成本/速度：测试数据中标记为待官方价格页确认。
- API 兼容性：模拟保持 Claude Messages API 兼容。

市场热度（模拟）：78/100
开发者讨论量（模拟）：GitHub/论坛相关信号约 126 条；Hacker News 相关讨论 18 条；相关仓库星标合计约 8.4k。

市场评论摘要（模拟）：
- 开发者主要关注它是否能替代 Sonnet/Opus 在长任务 Agent 场景中的位置。
- 企业用户关注价格、速率限制和上下文窗口是否同步升级。
- 创作者社区关注长篇写作一致性和可控风格。

重要人物/机构评价：暂未命中重大补充阈值。若后续出现 Elon Musk、Jensen Huang、Sam Altman、Dario Amodei 等高影响评价，系统会单独补推。

来源（模拟）：
> Anthropic News：claude-fable5 announcement（测试）
> Claude Models Docs：claude-fable5 model card（测试）
> Developer discussion scan：GitHub / Hacker News 热度快照（测试）
"""
    notifier.send_markdown("测试数据 claude-fable5", markdown)


def show_registry() -> None:
    settings = Settings()
    registry = load_registry(settings.registry_path)
    for provider in registry.providers:
        print(
            f"{provider.priority} {provider.id} {provider.name} "
            f"sources={len(provider.sources)} families={','.join(provider.model_families)}"
        )


def run_scheduler() -> None:
    settings = Settings()
    registry = load_registry(settings.registry_path)
    store = Store(settings.db_path)
    runner = MonitorRunner(settings, registry, store)

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        runner.run_once,
        "interval",
        minutes=settings.poll_interval_minutes,
        id="model-alert-scan",
        max_instances=1,
        coalesce=True,
        next_run_time=None,
    )
    print(f"[info] scheduler started; interval={settings.poll_interval_minutes} minutes")
    runner.run_once()
    scheduler.start()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", default="run", choices=["run", "once", "test", "sample", "registry"])
    parser.add_argument("--once", action="store_true", help="Run one scan and exit.")
    args = parser.parse_args()

    if args.once or args.command == "once":
        run_once()
    elif args.command == "test":
        send_test()
    elif args.command == "sample":
        send_sample()
    elif args.command == "registry":
        show_registry()
    else:
        try:
            run_scheduler()
        except KeyboardInterrupt:
            print("[info] stopped")
            time.sleep(0.1)


if __name__ == "__main__":
    main()
