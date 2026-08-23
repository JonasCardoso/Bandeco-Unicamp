"""Execução principal do bot Bandeco.

Este módulo configura e inicia o bot Telegram com todos os handlers,
comandos e jobs de notificação automática de cardápios.
"""

import datetime as dt
import logging
import os
import time

import pytz
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
    ra,
    reset_modalidade,
    reset_notificacao,
    reset_telefone,
    rs,
    ru,
    saldo,
    start,
    tabela,
    twitter,
)
from servico import notificar_cardapio
from util import (
    get_horario_almoco,
    get_horario_cafe,
    get_horario_jantar,
    get_token_bot_telegram,
    log_env_validation,
    validar_env_vars,
)

# =============================================================================
# Configuração do ambiente
# =============================================================================

os.environ["TZ"] = "America/Sao_Paulo"
time.tzset()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


def main():
    # Valida variáveis de ambiente obrigatórias antes de iniciar
    faltando = validar_env_vars()
    log_env_validation(faltando)
    if faltando:
        raise SystemExit(1)


    application = Application.builder().token(get_token_bot_telegram()).build()

    cafe_horario = dt.time(hour=get_horario_cafe(), minute=0, tzinfo=pytz.timezone('America/Sao_Paulo'))
    almoco_horario = dt.time(hour=get_horario_almoco(), minute=0, tzinfo=pytz.timezone('America/Sao_Paulo'))
    jantar_horario = dt.time(hour=get_horario_jantar(), minute=0, tzinfo=pytz.timezone('America/Sao_Paulo'))
    application.job_queue.run_daily(notificar_cardapio, cafe_horario, days=tuple(range(0, 7)), name='Café da manhã')
    application.job_queue.run_daily(notificar_cardapio, almoco_horario, days=tuple(range(0, 7)), name='Almoço')
    application.job_queue.run_daily(notificar_cardapio, jantar_horario, days=tuple(range(0, 7)), name='Jantar')

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler("cafe", cafe))
    application.add_handler(CommandHandler("almoco", almoco))
    application.add_handler(CommandHandler("jantar", jantar))
    application.add_handler(CommandHandler('modalidade', modalidade))
    application.add_handler(CommandHandler('notificacao', notificacao))
    application.add_handler(CommandHandler('horario', horario))
    application.add_handler(CommandHandler('saldo', saldo))
    application.add_handler(CommandHandler('contato', contato))
    application.add_handler(CommandHandler('ru', ru))
    application.add_handler(CommandHandler('ra', ra))
    application.add_handler(CommandHandler('rs', rs))
    application.add_handler(CommandHandler('tabela', tabela))
    application.add_handler(CommandHandler('twitter', twitter))
    application.add_handler(CommandHandler('instagram', instagram))
    application.add_handler(CommandHandler('facebook', facebook))
    application.add_handler(CommandHandler('desativar', desativar))
    application.add_handler(CommandHandler('reset-modalidade', reset_modalidade))
    application.add_handler(CommandHandler('reset-notificacao', reset_notificacao))
    application.add_handler(CommandHandler('reset-telefone', reset_telefone))
    application.add_handler(CommandHandler('ajuda', ajuda))
    application.add_handler(MessageHandler(filters.TEXT, mensagem))
    application.add_handler(MessageHandler(filters.CONTACT, mensagem_contato))

    application.run_polling()


if __name__ == '__main__':
    main()
