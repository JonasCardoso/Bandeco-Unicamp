"""Heartbeat interno usado pelo healthcheck do container."""

import time
from pathlib import Path

from core.settings import get_settings

HEALTHCHECK_FILE = Path(get_settings().healthcheck_file)
HEALTHCHECK_MAX_AGE_SECONDS = 90


def registrar_heartbeat() -> None:
    HEALTHCHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
    HEALTHCHECK_FILE.touch()


async def atualizar_heartbeat(_context) -> None:
    registrar_heartbeat()


def esta_saudavel(agora: float | None = None) -> bool:
    try:
        idade = (time.time() if agora is None else agora) - HEALTHCHECK_FILE.stat().st_mtime
    except OSError:
        return False
    return 0 <= idade <= HEALTHCHECK_MAX_AGE_SECONDS


def main() -> None:
    raise SystemExit(0 if esta_saudavel() else 1)


if __name__ == "__main__":
    main()
