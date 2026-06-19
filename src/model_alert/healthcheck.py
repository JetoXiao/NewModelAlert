from __future__ import annotations

from pathlib import Path

from .settings import Settings


def main() -> None:
    settings = Settings()
    if not Path(settings.registry_path).exists():
        raise SystemExit("registry missing")
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
