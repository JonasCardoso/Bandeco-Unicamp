"""Serviço principal de notificação de cardápios.

Este módulo orquestra a consulta de cardápios, formatação e envio
de notificações para Telegram, Twitter/X e Meta (Instagram/Facebook).
"""

import datetime as dt

from telegram.ext import CallbackContext

# =============================================================================
# Imports do projeto
# =============================================================================
from bandeco import comida
from cardapio import modalidade_com_cardapio
from config import Config as FirebaseConfig
from log import Log
from meta_servico import postar_meta
from ngrok_servico import Ngrok
from telegram_servico import mandar_mensagem
from twitter_servico import postar_tweet
from util import DIAS, get_horario_almoco, get_horario_cafe, get_horario_jantar


async def notificar_cardapio(context: CallbackContext) -> None:
    """Notifica todos os usuários sobre o cardápio do dia.

    Consulta o cardápio, gera as imagens e envia para Telegram,
    Twitter/X e Meta (Instagram/Facebook).

    Args:
        context: Contexto do bot Telegram.
    """
    log = Log()
    firebase = FirebaseConfig()
    ngrok = Ngrok()

    hoje = dt.datetime.today()
    cardapio_dia = comida(hoje.strftime('%Y-%m-%d'))

    if cardapio_dia is None:
        log.adicionar_log(f'notificarCardapio - {0} - Não foi possível consultar o cardápio')
        await log.enviar_log(context)
        return

    dados_periodo = ''
    modalidade = ''

    url = ngrok.iniciar_servidor(log)

    if hoje.hour == get_horario_cafe():
        dados_periodo = 'cafe'
        modalidade = 'Café da manhã'
    elif hoje.hour == get_horario_almoco():
        dados_periodo = 'almoco'
        modalidade = 'Almoço'
    elif hoje.hour == get_horario_jantar():
        dados_periodo = 'jantar'
        modalidade = 'Jantar'

    cardapio = modalidade_com_cardapio(
        cardapio_dia, {"tradicional": 1, "vegano": 1, "cafe": 1, "almoco": 1, "jantar": 1}, modalidade
    )
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
            cardapio = modalidade_com_cardapio(cardapio_dia, dados, modalidade)
            await mensagem_cardapio_telegram(id_usuario, context, cardapio, hoje)


async def mensagem_cardapio_telegram(id_usuario, context: CallbackContext, cardapio, dia) -> None:
    """Envia o cardápio para um usuário via Telegram.

    Args:
        id_usuario: ID do chat ou username do destinatário.
        context: Contexto do bot Telegram.
        cardapio: Lista de tuplas (prato, modalidade).
        dia: Data do cardápio.
    """
    for item, modalidade in cardapio:
        if not(item == 'Refeição não cadastrada.' and id_usuario == '@bandecounicamp'):
            await mandar_mensagem(
                context, id_usuario,
                f'*{modalidade} de {DIAS[dia.weekday()]}* \n\n{item}'
            )


async def mensagem_cardapio_twitter(context: CallbackContext, cardapio, dia) -> None:
    """Publica o cardápio no Twitter/X.

    Args:
        context: Contexto do bot Telegram.
        cardapio: Lista de tuplas (prato, modalidade).
        dia: Data do cardápio.
    """
    log = Log()

    for item, modalidade in cardapio:
        if item != 'Refeição não cadastrada.':
            await postar_tweet(
                context, f'{modalidade} de {DIAS[dia.weekday()]}', item, log
            )


async def mensagem_cardapio_meta(context: CallbackContext, cardapio, dia, url) -> None:
    """Publica o cardápio no Meta (Instagram/Facebook).

    Args:
        context: Contexto do bot Telegram.
        cardapio: Lista de tuplas (prato, modalidade).
        dia: Data do cardápio.
        url: URL pública do servidor ngrok.
    """
    log = Log()

    for item, modalidade in cardapio:
        if item != 'Refeição não cadastrada.':
            await postar_meta(
                context, f'{modalidade} de {DIAS[dia.weekday()]}', item, log, url
            )
