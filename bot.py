import datetime as dt
import logging
import os
import pytz
import time

from telegram.ext import Updater, CommandHandler, Filters, MessageHandler
from comando import start, cafe, almoco, jantar, modalidade, notificacao, saldo, ru, ra, rs, horario, ajuda, mensagem, \
    contato, twitter, instagram, desativar, mensagemContato
from servico import notificarCardapio
from util import HORARIO_CAFE, HORARIO_ALMOCO, HORARIO_JANTAR, TOKEN_BOT_TELEGRAM, URL_SERVICO

os.environ["TZ"] = 'America/Sao_Paulo'
time.tzset()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def main():
    updater = Updater(token=TOKEN_BOT_TELEGRAM, use_context=True)

    cafeHorario = dt.time(hour=int(HORARIO_CAFE), minute=0, tzinfo=pytz.timezone('America/Sao_Paulo'))
    almocoHorario = dt.time(hour=int(HORARIO_ALMOCO), minute=0, tzinfo=pytz.timezone('America/Sao_Paulo'))
    jantarHorario = dt.time(hour=int(HORARIO_JANTAR), minute=0, tzinfo=pytz.timezone('America/Sao_Paulo'))
    updater.job_queue.run_daily(notificarCardapio, cafeHorario, days=tuple(range(5)), context='Café da manhã',
                                name='Café da manhã')
    updater.job_queue.run_daily(notificarCardapio, almocoHorario, days=tuple(range(5)), context='Almoço', name='Almoço')
    updater.job_queue.run_daily(notificarCardapio, jantarHorario, days=tuple(range(5)), context='Jantar', name='Jantar')

    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    cafe_handler = CommandHandler("cafe", cafe)
    almoco_handler = CommandHandler("almoco", almoco)
    jantar_handler = CommandHandler("jantar", jantar)
    modalidade_handler = CommandHandler('modalidade', modalidade)
    notificacao_handler = CommandHandler('notificacao', notificacao)
    horario_handler = CommandHandler('horario', horario)
    saldo_handler = CommandHandler('saldo', saldo)
    contato_handler = CommandHandler('contato', contato)
    ru_handler = CommandHandler('ru', ru)
    ra_handler = CommandHandler('ra', ra)
    rs_handler = CommandHandler('rs', rs)
    twitter_handler = CommandHandler('twitter', twitter)
    instagram_handler = CommandHandler('instagram', instagram)
    desativar_handler = CommandHandler('desativar', desativar)
    ajuda_handler = CommandHandler('ajuda', ajuda)
    mensagem_handler = MessageHandler(Filters.text, mensagem)
    mensagemContato_handler = MessageHandler(Filters.contact, mensagemContato)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(cafe_handler)
    dispatcher.add_handler(almoco_handler)
    dispatcher.add_handler(jantar_handler)
    dispatcher.add_handler(modalidade_handler)
    dispatcher.add_handler(notificacao_handler)
    dispatcher.add_handler(horario_handler)
    dispatcher.add_handler(saldo_handler)
    dispatcher.add_handler(contato_handler)
    dispatcher.add_handler(ru_handler)
    dispatcher.add_handler(ra_handler)
    dispatcher.add_handler(rs_handler)
    dispatcher.add_handler(twitter_handler)
    dispatcher.add_handler(instagram_handler)
    dispatcher.add_handler(desativar_handler)
    dispatcher.add_handler(ajuda_handler)
    dispatcher.add_handler(mensagem_handler)
    dispatcher.add_handler(mensagemContato_handler)

    PORT = int(os.environ.get('PORT', '8443'))
    HOOK_URL = URL_SERVICO + TOKEN_BOT_TELEGRAM
    updater.start_webhook(listen='0.0.0.0', port=PORT, url_path=TOKEN_BOT_TELEGRAM, webhook_url=HOOK_URL)
    updater.idle()

    # updater.start_polling() # usar esse ou as 4 linhas acimas, heroku fica melhor no acima


if __name__ == '__main__':
    main()
