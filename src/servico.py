from telegram.ext import CallbackContext

import bandeco
import config
import datetime as dt
import meta_servico
import log as lg
import telegram_servico
import twitter_servico
import ngrok_servico
from util import DIAS, MODALIDADES, HORARIO_CAFE, HORARIO_ALMOCO, HORARIO_JANTAR

log = lg.Log()
firebase = config.Config()
ngrok = ngrok_servico.Ngrok()


async def notificar_cardapio(context: CallbackContext):
    hoje = dt.datetime.today()
    comida = bandeco.comida(hoje.strftime('%Y-%m-%d'))

    if comida is None:
        log.adicionar_log(f'notificarCardapio - {0} - Não foi possível consultar o cardápio')
        await log.enviar_log(context)
        return

    dados_periodo = ''
    modalidade = ''

    url = ngrok.iniciar_servidor(log)

    if hoje.hour == HORARIO_CAFE:
        dados_periodo = 'cafe'
        modalidade = 'Café da manhã'
    elif hoje.hour == HORARIO_ALMOCO:
        dados_periodo = 'almoco'
        modalidade = 'Almoço'
    elif hoje.hour == HORARIO_JANTAR:
        dados_periodo = 'jantar'
        modalidade = 'Jantar'

    cardapio = modalidade_com_cardapio(comida, {"tradicional": 1, "vegano": 1, "cafe": 1, "almoco": 1, "jantar": 1},
                                       modalidade)
    await mensagem_cardapio_telegram('@bandecounicamp', context, cardapio, hoje)
    await mensagem_cardapio_twitter(context, cardapio, hoje)
    await mensagem_cardapio_meta(context, cardapio, hoje, url)

    ngrok.desligar_servidor(log)
    await log.enviar_log(context)

    usuarios = firebase.pegar_todos_usuarios()
    if not usuarios:
        log.adicionar_log(f'notificarCardapio - {0} - Não foi possível pegar todos usuários')
        await log.enviar_log(context)
        return

    for id_usuario, dados in usuarios.items():
        if dados[dados_periodo] == 1:
            cardapio = modalidade_com_cardapio(comida, dados, modalidade)
            await mensagem_cardapio_telegram(id_usuario, context, cardapio, hoje)


def modalidade_com_cardapio(comida, dados, periodo):
    cardapio = list()

    if 'Café da manhã' == periodo:
        cardapio.append([comida[4], MODALIDADES[4]])

    elif 'Almoço' == periodo:
        if dados['tradicional'] == 1:
            cardapio.append([comida[0], MODALIDADES[0]])
        if dados['vegano'] == 1:
            cardapio.append([comida[1], MODALIDADES[1]])
        if dados['tradicional'] == 0 and dados['vegano'] == 0:
            cardapio.append([comida[0], MODALIDADES[0]])
            cardapio.append([comida[1], MODALIDADES[1]])

    elif 'Jantar' == periodo:
        if dados['tradicional'] == 1:
            cardapio.append([comida[2], MODALIDADES[2]])
        if dados['vegano'] == 1:
            cardapio.append([comida[3], MODALIDADES[3]])
        if dados['tradicional'] == 0 and dados['vegano'] == 0:
            cardapio.append([comida[2], MODALIDADES[2]])
            cardapio.append([comida[3], MODALIDADES[3]])

    return cardapio


async def mensagem_cardapio_telegram(id_usuario, context, cardapio, dia):
    for item, modalidade in cardapio:
        await telegram_servico.mandar_mensagem(context, id_usuario, f'*{modalidade} de {DIAS[dia.weekday()]}'
                                                                    f'* \n\n{item}')


async def mensagem_cardapio_twitter(context, cardapio, dia):
    for item, modalidade in cardapio:
        await twitter_servico.postar_tweet(context, f'{modalidade} de {DIAS[dia.weekday()]}', item, log)


async def mensagem_cardapio_meta(context, cardapio, dia, url):
    for item, modalidade in cardapio:
        await meta_servico.postar_meta(context, f'{modalidade} de {DIAS[dia.weekday()]}', item, log, url)
