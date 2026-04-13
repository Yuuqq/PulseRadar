# External Integrations

## Data Sources — Hot Lists (Crawlers)

Crawled via `trendradar/crawler/` with plugin architecture. API source: configurable via `advanced.crawler.api_url` or direct scraping.

**Configured platforms** (from `config/config.yaml` `platforms.sources`):
- 今日头条, 百度热搜, 华尔街见闻, 澎湃新闻, bilibili 热搜, 财联社热门
- 凤凰网, 贴吧, 微博, 抖音, 知乎, 36氪, 少数派, 掘金, 人人都是产品经理
- Hacker News, Product Hunt, GitHub Trending, V2EX, 36氪快讯, 酷安

## Data Sources — Extra APIs

Plugin-based crawlers in `trendradar/crawler/plugins/`:
- `vvhan.py` — VVHan API (微博热搜等)
- `dailyhot.py` — DailyHot aggregated hot lists
- `newsapi.py` — NewsAPI.org
- `gnews.py` — GNews API
- `mediastack.py` — MediaStack API
- `thenewsapi.py` — TheNewsAPI
- `eastmoney.py` — 东方财富
- `tonghuashun.py` — 同花顺
- `wallstreetcn.py` — 华尔街见闻

## Data Sources — RSS Feeds

Parsed via `feedparser` in `trendradar/crawler/rss/`:
- 60+ configurable RSS feeds in `config/config.yaml` (Hacker News, BBC, NYT, Reuters, arXiv, etc.)
- Freshness filter: `rss.freshness_filter.max_age_days` (default: 3 days)

## AI Integration

- **Client:** `trendradar/ai/client.py` — unified via LiteLLM (`litellm.completion`)
- **Provider:** Any LiteLLM-supported provider (OpenAI, DeepSeek, Gemini, Claude, etc.)
- **Features:**
  - AI analysis of news trends (`trendradar/ai/analyzer.py`)
  - AI translation of content (`trendradar/ai/translator.py`)
  - Configurable model, temperature, max_tokens, fallback models
- **Prompt files:** `config/ai_analysis_prompt.txt`, `config/ai_translation_prompt.txt`

## Notification Channels

Dispatched via `trendradar/notification/dispatcher.py`. Each channel supports multi-account (`;`-separated).

| Channel | Module | Config Key |
|---------|--------|------------|
| Feishu (飞书) | `channels/feishu.py` | `FEISHU_WEBHOOK_URL` |
| DingTalk (钉钉) | `channels/dingtalk.py` | `DINGTALK_WEBHOOK_URL` |
| WeCom (企业微信) | `channels/wework.py` | `WEWORK_WEBHOOK_URL` |
| Telegram | `channels/telegram.py` | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` |
| Slack | `channels/slack.py` | `SLACK_WEBHOOK_URL` |
| Email | `channels/email.py` | `EMAIL_FROM`, `EMAIL_PASSWORD`, `EMAIL_SMTP_SERVER` |
| Bark | `channels/bark.py` | `BARK_URL` |
| ntfy | `channels/ntfy.py` | `NTFY_TOPIC` + `NTFY_SERVER_URL` |
| Generic Webhook | `channels/webhook.py` | `GENERIC_WEBHOOK_URL` |

## Storage Backends

Managed via `trendradar/storage/manager.py`:

- **Local SQLite** — `trendradar/storage/local.py`, schema in `storage/schema.sql` and `storage/rss_schema.sql`
- **Remote S3** — `trendradar/storage/remote.py`, S3-compatible (AWS, MinIO, etc.) via boto3
- **Auto mode** — GitHub Actions → remote; Docker/local → local
- **Output formats:** SQLite (.db), HTML reports, TXT snapshots (configurable)

## MCP Server

`mcp_server/server.py` — FastMCP 2.0 server exposing tools for AI assistants:
- **Tools:** data query, analytics, search, config management, system management, storage sync, article reader
- **Resources:** `config://platforms`, `config://rss-feeds`, `data://available-dates`
- **Transport:** stdio and HTTP (port 3333 in Docker)

## CI/CD

- **GitHub Actions:** `.github/workflows/crawler.yml` — scheduled hourly cron with 7-day check-in cycle
- **Docker:** `.github/workflows/docker.yml` — image build and publish
- **Cleanup:** `.github/workflows/clean-crawler.yml` — workflow cleanup

## Version Checking

Remote version checking against GitHub raw files:
- `advanced.version_check_url` → `version` file
- `advanced.configs_version_check_url` → `version_configs` file
- `advanced.mcp_version_check_url` → `version_mcp` file
