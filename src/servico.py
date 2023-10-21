from telegram.ext import CallbackContext

import bandeco
import config
import datetime as dt
import metaServico
import log as lg
import telegramServico
import twitterServico
from util import DIAS, MODALIDADES, HORARIO_CAFE, HORARIO_ALMOCO, HORARIO_JANTAR

log = lg.Log()
firebase = config.Config()


async def notificarCardapio(context: CallbackContext):
    usuarios = firebase.pegarTodosUsuarios()
    if not usuarios:
        log.adicionarLog(f'notificarCardapio - {0} - Não foi possível pegar todos usuários')
        await log.enviarLog(context)
        return

    hoje = dt.datetime.today()
    comida = bandeco.comida(hoje.strftime('%Y-%m-%d'))

    if comida is None:
        log.adicionarLog(f'notificarCardapio - {0} - Não foi possível consultar o cardápio')
        await log.enviarLog(context)
        return

    dadosPeriodo = ''
    modalidade = ''

    if hoje.hour == HORARIO_CAFE:
        dadosPeriodo = 'cafe'
        modalidade = 'Café da manhã'
    elif hoje.hour == HORARIO_ALMOCO:
        dadosPeriodo = 'almoco'
        modalidade = 'Almoço'
    elif hoje.hour == HORARIO_JANTAR:
        dadosPeriodo = 'jantar'
        modalidade = 'Jantar'

    cardapio = modalidadeComCardapio(comida, {"tradicional": 1, "vegano": 1, "cafe": 1, "almoco": 1, "jantar": 1},
                                     modalidade)
    await mensagemCardapioTelegram('@bandecounicamp', context, cardapio, hoje)
    await mensagemCardapioTwitter(context, cardapio, hoje)
    await mensagemCardapioInstagram(context, cardapio, hoje)

    for id, dados in usuarios.items():
       if dados[dadosPeriodo] == 1:
            cardapio = modalidadeComCardapio(comida, dados, modalidade)
            await mensagemCardapioTelegram(id, context, cardapio, hoje)


def modalidadeComCardapio(comida, dados, periodo):
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


async def mensagemCardapioTelegram(id, context, cardapio, dia):
    for item, modalidade in cardapio:
        await telegramServico.mandarMensagem(context, id, f'* {modalidade} de {DIAS[dia.weekday()]} * \n\n{item}')


async def mensagemCardapioTwitter(context, cardapio, dia):
    for item, modalidade in cardapio:
        await twitterServico.postarTweet(context, f'{modalidade} de {DIAS[dia.weekday()]}', item, log)


async def mensagemCardapioInstagram(context, cardapio, dia):
    for item, modalidade in cardapio:
        await metaServico.postarInsta(context, f'{modalidade} de {DIAS[dia.weekday()]}', item, log)
