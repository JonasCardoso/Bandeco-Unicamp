"""Execução principal do bot Bandeco.

Este módulo configura e inicia o bot Telegram com todos os handlers,
comandos e jobs de notificação automática de cardápios.
"""

import datetime as dt
import logging
import os
import time
from zoneinfo import ZoneInfo

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from comando import (
    ajuda,
    almoco,
    cafe,
    contato,
    desativar,
    facebook,
    horario,
    instagram,
    jantar,
    mensagem,
    mensagem_contato,
    modalidade,
    notificacao,
    preco,
    ra,
    reset_contato,
    reset_modalidade,
    reset_notificacao,
    rs,
    ru,
    saldo,
    start,
    tabela,
    twitter,
)
from config import get_firebase
from servico import notificar_cardapio
from util import (
    get_horario_almoco,
    get_horario_cafe,
    get_horario_jantar,
    get_token_bot_telegram,
    log_env_validation,
    validar_env_vars,
)

logger = logging.getLogger(__name__)
FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")


def configurar_runtime() -> None:
    """Configura timezone e logging somente durante o startup explícito."""
    os.environ.setdefault("TZ", "America/Sao_Paulo")
    if hasattr(time, "tzset"):
        time.tzset()
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)


def main():
    configurar_runtime()
    # Valida variáveis de ambiente obrigatórias antes de iniciar
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

    cafe_horario = dt.time(hour=get_horario_cafe(), minute=0, tzinfo=FUSO_HORARIO)
    almoco_horario = dt.time(hour=get_horario_almoco(), minute=0, tzinfo=FUSO_HORARIO)
    jantar_horario = dt.time(hour=get_horario_jantar(), minute=0, tzinfo=FUSO_HORARIO)
    application.job_queue.run_daily(notificar_cardapio, cafe_horario, days=tuple(range(0, 7)), name="Café da manhã")
    application.job_queue.run_daily(notificar_cardapio, almoco_horario, days=tuple(range(0, 7)), name="Almoço")
    application.job_queue.run_daily(notificar_cardapio, jantar_horario, days=tuple(range(0, 7)), name="Jantar")

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cafe", cafe))
    application.add_handler(CommandHandler("almoco", almoco))
    application.add_handler(CommandHandler("jantar", jantar))
    application.add_handler(CommandHandler("modalidade", modalidade))
    application.add_handler(CommandHandler("notificacao", notificacao))
    application.add_handler(CommandHandler("horario", horario))
    application.add_handler(CommandHandler("saldo", saldo))
    application.add_handler(CommandHandler("contato", contato))
    application.add_handler(CommandHandler("ru", ru))
    application.add_handler(CommandHandler("ra", ra))
    application.add_handler(CommandHandler("rs", rs))
    application.add_handler(CommandHandler("tabela", tabela))
    application.add_handler(CommandHandler("preco", preco))
    application.add_handler(CommandHandler("twitter", twitter))
    application.add_handler(CommandHandler("instagram", instagram))
    application.add_handler(CommandHandler("facebook", facebook))
    application.add_handler(CommandHandler("desativar", desativar))
    application.add_handler(CommandHandler("reset_modalidade", reset_modalidade))
    application.add_handler(CommandHandler("reset_notificacao", reset_notificacao))
    application.add_handler(CommandHandler("reset_contato", reset_contato))
    application.add_handler(CommandHandler("ajuda", ajuda))
    application.add_handler(MessageHandler(filters.TEXT, mensagem))
    application.add_handler(MessageHandler(filters.CONTACT, mensagem_contato))

    application.run_polling()


if __name__ == "__main__":
    main()
