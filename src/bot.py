import datetime as dt
import logging
import os
import pytz
import time

from telegram.ext import CommandHandler, filters, MessageHandler, Application
from comando import start, cafe, almoco, jantar, modalidade, notificacao, saldo, ru, ra, rs, horario, ajuda, mensagem, \
    contato, twitter, instagram, desativar, mensagem_contato
from servico import notificar_cardapio
from util import HORARIO_CAFE, HORARIO_ALMOCO, HORARIO_JANTAR, TOKEN_BOT_TELEGRAM

os.environ["TZ"] = 'America/Sao_Paulo'
time.tzset()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def main():
    application = Application.builder().token(TOKEN_BOT_TELEGRAM).build()

    cafe_horario = dt.time(hour=int(HORARIO_CAFE), minute=0, tzinfo=pytz.timezone('America/Sao_Paulo'))
    almoco_horario = dt.time(hour=int(HORARIO_ALMOCO), minute=0, tzinfo=pytz.timezone('America/Sao_Paulo'))
    jantar_horario = dt.time(hour=int(HORARIO_JANTAR), minute=0, tzinfo=pytz.timezone('America/Sao_Paulo'))
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
    application.add_handler(CommandHandler('twitter', twitter))
    application.add_handler(CommandHandler('instagram', instagram))
    application.add_handler(CommandHandler('desativar', desativar))
    application.add_handler(CommandHandler('ajuda', ajuda))
    application.add_handler(MessageHandler(filters.TEXT, mensagem))
    application.add_handler(MessageHandler(filters.CONTACT, mensagem_contato))

    application.run_polling()


if __name__ == '__main__':
    main()
