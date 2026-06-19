from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    registry_path: Path = Path(os.getenv("REGISTRY_PATH", "config/providers.yaml"))
    db_path: Path = Path(os.getenv("DB_PATH", "data/model_alert.sqlite3"))
    poll_interval_minutes: int = int(os.getenv("POLL_INTERVAL_MINUTES", "30"))
    event_settle_minutes: int = int(os.getenv("EVENT_SETTLE_MINUTES", "45"))
    bootstrap_notify: bool = _bool_env("BOOTSTRAP_NOTIFY", False)
    dry_run: bool = _bool_env("DRY_RUN", False)
    wechat_webhook_url: str = os.getenv("WECHAT_WEBHOOK_URL", "")
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "")
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
    user_agent: str = os.getenv(
        "USER_AGENT",
        "new-model-alert/0.1 (+https://example.local; quiet AI model monitor)",
    )

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key and self.llm_model)
