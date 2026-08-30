"""Composição e inicialização explícita da aplicação."""

import logging
import os
import time

from telegram.ext import Application, CommandHandler, MessageHandler

from app.registry import register_handlers
from app.scheduler import schedule_jobs
from core.config import (
    get_horario_almoco,
    get_horario_cafe,
    get_horario_jantar,
    get_token_bot_telegram,
    log_env_validation,
    validar_env_vars,
)
from core.settings import get_settings
from integrations.firebase.user_repository import get_firebase

logger = logging.getLogger(__name__)


def configurar_runtime() -> None:
    """Configura timezone e logging somente durante o startup explícito."""
    os.environ.setdefault("TZ", "America/Sao_Paulo")
    if hasattr(time, "tzset"):
        time.tzset()
    nivel = getattr(logging, get_settings().log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=nivel)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)


def main() -> None:
    configurar_runtime()
    faltando = validar_env_vars()
    log_env_validation(faltando)
    if faltando:
        raise SystemExit(1)

    logger.info("Inicializando Firebase...")
    try:
        get_firebase()
    except (ValueError, OSError) as erro:
        logger.exception("Falha ao inicializar Firebase; o bot não será iniciado.")
        raise SystemExit(1) from erro

    application = Application.builder().token(get_token_bot_telegram()).build()
    schedule_jobs(application, get_horario_cafe(), get_horario_almoco(), get_horario_jantar())
    register_handlers(application, CommandHandler, MessageHandler)
    application.run_polling()


if __name__ == "__main__":
    main()
