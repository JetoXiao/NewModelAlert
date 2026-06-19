# New Model Alert

一个安静型大模型情报监控器：监控主流大模型厂商的新模型发布、模型更新和下架信息，并通过企业微信推送一条聚合后的高质量消息。默认策略是少打扰：同一模型事件只推送一次主消息，后续只有重大新闻、重要人物评价或市场热度显著升高时才补充推送。

## 特点

- 可扩展厂商注册表：新增厂商通常只需要改 `config/providers.yaml`
- 首次启动只建立基线，避免把历史消息刷屏
- 官方来源优先，支持可信度分级
- 事件沉淀窗口内自动聚合多个来源，一次性推送
- 支持 Hacker News / GitHub 的市场热度和开发者讨论量统计
- Docker Compose 隔离部署，不暴露端口，不挂载 Docker socket，不影响同机其他容器

## 快速开始

```bash
cp .env.example .env
# 编辑 .env，填入 WECHAT_WEBHOOK_URL
docker compose up -d --build
```

本地试跑一次：

```bash
DRY_RUN=true python -m model_alert --once
```

如果没有配置 `WECHAT_WEBHOOK_URL`，程序不会报错退出，而是把推送内容打印到日志里，方便先 dry-run。

## 推送策略

主推送触发条件：

- 厂商官方公告、官方文档、模型目录或价格页出现新模型、更新、下架、弃用等信号
- 或多个可信来源交叉确认
- 事件等待 `EVENT_SETTLE_MINUTES` 后统一聚合推送

补充推送触发条件：

- 已推送事件出现重大后续，例如官方补充说明、价格/能力/兼容性重大变化
- 重要人物或机构评价，例如 Elon Musk、Jensen Huang、Sam Altman、Dario Amodei、Demis Hassabis 等
- 市场热度或开发者讨论量相比主推送时明显跃升

默认不会因为普通媒体转述、社区零散讨论、重复榜单搬运而补推。系统会在主推送里尽量一次性包含评分、具体更新内容、市场热度和开发者讨论量，后续只在事件影响力显著变化时再打扰你。

## 常用命令

```bash
# 查看当前监控厂商注册表
docker compose run --rm model-alert model-alert registry

# 发送企业微信测试消息
docker compose run --rm model-alert model-alert test

# 只扫描一次并退出
docker compose run --rm -e DRY_RUN=true model-alert model-alert once
```

## 运行安全

`docker-compose.yml` 默认：

- 不使用 host network
- 不暴露端口
- 不挂载宿主机 Docker socket
- 只读容器文件系统
- 限制 CPU 和内存
- 限制日志大小
- 独立 bridge 网络

## 配置文件

- `config/providers.yaml`：厂商注册表和来源配置
- `data/model_alert.sqlite3`：本地状态库

## 说明

没有配置 `LLM_API_KEY` 时，系统仍会推送基于规则的摘要、评分和热度统计；配置 LLM 后，摘要质量会更好，但系统会要求模型严格基于已采集来源生成，不把未经确认的信息写成事实。
