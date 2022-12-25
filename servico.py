from telegram.ext import CallbackContext

import bandeco
import config
import datetime as dt
import instagramServico
import log as lg
import telegramServico
import twitterServico
from util import DIAS, MODALIDADES

log = lg.Log()
firebase = config.Config()
instagram = instagramServico.Instagram()


def notificarCardapio(context: CallbackContext):
    usuarios = firebase.pegarTodosUsuarios()
    if not usuarios:
        log.adicionarLog(f'notificarCardapio - {0} - Não foi possível pegar todos usuários')
        log.enviarLog(context)
        return

    hoje = dt.datetime.today()
    comida = bandeco.comida(hoje.strftime('%Y-%m-%d'))

    if comida is None:
        log.adicionarLog(f'notificarCardapio - {0} - Não foi possível consultar o cardápio')
        log.enviarLog(context)
        return

    dadosPeriodo = ''
    if context.job.context == 'Café da manhã':
        dadosPeriodo = 'cafe'
    elif context.job.context == 'Almoço':
        dadosPeriodo = 'almoco'
    elif context.job.context == 'Jantar':
        dadosPeriodo = 'jantar'

    cardapio = modalidadeComCardapio(comida, {"tradicional": 1, "vegano": 1, "cafe": 1, "almoco": 1, "jantar": 1},
                                     context.job.context)
    mensagemCardapioTelegram('@bandecounicamp', context, cardapio, hoje)
    mensagemCardapioTwitter(context, cardapio, hoje)
    #mensagemCardapioInstagram(context, cardapio, hoje)

    for id, dados in usuarios.items():
        if dados[dadosPeriodo] == 1:
            cardapio = modalidadeComCardapio(comida, dados, context.job.context)
            mensagemCardapioTelegram(id, context, cardapio, hoje)


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


def mensagemCardapioTelegram(id, context, cardapio, dia):
    for item, modalidade in cardapio:
        telegramServico.mandarMensagem(context, id, f'* {modalidade} de {DIAS[dia.weekday()]} * \n\n{item}')


def mensagemCardapioTwitter(context, cardapio, dia):
    for item, modalidade in cardapio:
        twitterServico.postarTweet(context, f'{modalidade} de {DIAS[dia.weekday()]}', item, log)


def mensagemCardapioInstagram(context, cardapio, dia):
    for item, modalidade in cardapio:
        instagram.postarInsta(context, f'{modalidade} de {DIAS[dia.weekday()]}', item, log)
