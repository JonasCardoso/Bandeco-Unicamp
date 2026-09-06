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


def registrar_rotina(nome: str, inicio: str, resultado: str) -> None:
    """Um arquivo por rotina evita sobrescrever resultados de jobs concorrentes."""
    import json
    from datetime import datetime, timezone

    destino = HEALTHCHECK_FILE.parent / f"{HEALTHCHECK_FILE.name}.{nome}.json"
    temporario = destino.with_suffix(".tmp")
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario.write_text(
        json.dumps({"inicio": inicio, "fim": datetime.now(timezone.utc).isoformat(), "resultado": resultado}),
        encoding="utf-8",
    )
    temporario.replace(destino)
