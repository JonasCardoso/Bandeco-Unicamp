"""Serviço principal de notificação de cardápios.

Este módulo orquestra a consulta de cardápios, formatação e envio
de notificações para Telegram, Twitter/X e Meta (Instagram/Facebook).
"""

import asyncio
import datetime as dt
import logging
import time

from telegram.ext import CallbackContext

from core.constants import DIAS
from integrations.firebase.user_repository import get_firebase
from integrations.social.meta import postar_meta
from integrations.social.twitter import postar_tweet

# =============================================================================
# Imports do projeto
# =============================================================================
from integrations.unicamp.menu_client import comida
from interfaces.telegram.logging import Log
from interfaces.telegram.messaging import mandar_mensagem
from modules.menu.service import modalidade_com_cardapio
from modules.preferences.rules import deve_notificar
from shared.keyed_lock import user_lock
from shared.text import fragmentos

logger = logging.getLogger(__name__)


async def notificar_cardapio(context: CallbackContext) -> None:
    """Cada integração progride independentemente; o job informa a refeição."""
    from modules.menu.view import FUSO, REFEICOES
    from shared.health import registrar_rotina

    hoje = dt.datetime.now(FUSO)
    periodo = context.job.data["refeicao"]
    inicio = hoje.isoformat()
    try:
        dados = await asyncio.to_thread(comida, hoje.date().isoformat())
        if dados is None:
            registrar_rotina(periodo, inicio, "fonte_indisponivel")
            return
        cardapio = modalidade_com_cardapio(dados, {"tradicional": 1, "vegano": 1}, REFEICOES[periodo])

        async def executar(nome, funcao):
            try:
                resultado = await funcao()
                registrar_rotina(f"{periodo}_{nome}", inicio, "parcial" if resultado is False else "concluido")
                return resultado is not False
            except Exception:
                logger.exception("Falha na rotina %s", nome)
                registrar_rotina(f"{periodo}_{nome}", inicio, "falha")
                return False

        resultados = await asyncio.gather(
            executar("telegram", lambda: entregar_telegram(context, dados, cardapio, hoje, periodo)),
            executar("twitter", lambda: mensagem_cardapio_twitter(context, cardapio, hoje)),
            executar("meta", lambda: mensagem_cardapio_meta(context, cardapio, hoje)),
        )
        registrar_rotina(periodo, inicio, "concluido" if all(resultados) else "parcial")
    except Exception:
        registrar_rotina(periodo, inicio, "falha")
        raise


async def entregar_telegram(context, dados_cardapio, cardapio, dia, periodo):
    from integrations.firebase.delivery_repository import DeliveryRepository
    from interfaces.telegram.delivery import DeliverySender
    from modules.menu.view import REFEICOES

    repo = get_firebase()
    entregas = await asyncio.to_thread(DeliveryRepository)
    sender = context.bot_data.setdefault("delivery_sender", DeliverySender())
    sucesso = True
    inicio = time.monotonic()
    contagens = {}

    async def destino(chat_id, itens, silencioso=False):
        nonlocal sucesso
        for item, modalidade in itens:
            if not item or item == "Refeição não cadastrada.":
                continue
            chave = f"{dia:%Y-%m-%d}_{periodo}_{'vegano' if 'Vegano' in modalidade else 'tradicional'}"
            partes = fragmentos(f"{modalidade.capitalize()} - {dia:%d/%m/%Y}\n\n{item}")
            for indice, texto in enumerate(partes):
                chave_parte = chave if len(partes) == 1 else f"{chave}_p{indice}"
                token = await asyncio.to_thread(entregas.reservar, chat_id, chave_parte)
                if token is None:
                    estado = await asyncio.to_thread(entregas.estado, chat_id, chave_parte)
                    contagens[estado] = contagens.get(estado, 0) + 1
                    sucesso = sucesso and estado == "confirmado"
                    continue
                resultado = await sender.enviar(
                    context.bot,
                    chat_id,
                    texto,
                    links_cardapio(dia, periodo, modalidade),
                    silencioso,
                    destacar_titulo=indice == 0,
                )
                estado = resultado.erro or "confirmado"
                contagens[estado] = contagens.get(estado, 0) + 1
                await asyncio.to_thread(entregas.concluir, chat_id, chave_parte, token, estado, resultado.message_id)
                if resultado.erro:
                    sucesso = False
                if resultado.erro == "bloqueado" and str(chat_id).isdecimal():
                    await asyncio.to_thread(repo.definir_preferencias, chat_id, {"bloqueado": True})
                if resultado.erro:
                    break

    await destino("@bandecounicamp", cardapio)
    usuarios = await asyncio.to_thread(repo.pegar_todos_usuarios)
    if usuarios is False:
        return False
    for id_usuario in usuarios:
        async with user_lock(context.bot_data, id_usuario):
            # Releitura impede usar preferências anteriores a uma pausa/exclusão.
            dados = await asyncio.to_thread(repo.pegar_usuario, id_usuario)
            if not deve_notificar(dados or {}, periodo, dia.weekday()):
                continue
            await destino(
                id_usuario,
                modalidade_com_cardapio(dados_cardapio, dados, REFEICOES[periodo]),
                bool(dados.get("silencioso", False)),
            )
    logger.info("telegram_entregas estados=%s duracao=%.3f", contagens, time.monotonic() - inicio)
    return sucesso


def links_cardapio(dia, periodo, modalidade):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    from core.config import get_bot_username

    username = get_bot_username().lstrip("@")
    tipo = "vegano" if "Vegano" in modalidade else "tradicional"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Abrir no bot", url=f"https://t.me/{username}?start=cardapio_{periodo}_{dia:%Y-%m-%d}_{tipo}"
                )
            ],
            [InlineKeyboardButton("Configurar notificações", url=f"https://t.me/{username}?start=preferencias")],
        ]
    )


async def mensagem_cardapio_telegram(id_usuario, context: CallbackContext, cardapio, dia) -> None:
    """Envia o cardápio para um usuário via Telegram.

    Args:
        id_usuario: ID do chat ou username do destinatário.
        context: Contexto do bot Telegram.
        cardapio: Lista de tuplas (prato, modalidade).
        dia: Data do cardápio.
    """
    for item, modalidade in cardapio:
        if not (item == "Refeição não cadastrada." and id_usuario == "@bandecounicamp"):
            await mandar_mensagem(context, id_usuario, f"*{modalidade.capitalize()} - {dia:%d/%m/%Y}* \n\n{item}")


async def mensagem_cardapio_twitter(context: CallbackContext, cardapio, dia) -> bool:
    """Publica o cardápio no Twitter/X.

    Args:
        context: Contexto do bot Telegram.
        cardapio: Lista de tuplas (prato, modalidade).
        dia: Data do cardápio.
    """
    log = Log()
    sucesso = True

    for item, modalidade in cardapio:
        if item and item != "Refeição não cadastrada.":
            resultado = await postar_tweet(context, f"{modalidade} de {DIAS[dia.weekday()]}", item, log)
            sucesso = resultado is not False and sucesso

    await log.enviar_log(context)
    return sucesso


async def mensagem_cardapio_meta(context: CallbackContext, cardapio, dia) -> bool:
    """Publica o cardápio no Meta (Instagram/Facebook).

    Args:
        context: Contexto do bot Telegram.
        cardapio: Lista de tuplas (prato, modalidade).
        dia: Data do cardápio.
    """
    log = Log()
    sucesso = True

    for item, modalidade in cardapio:
        if item and item != "Refeição não cadastrada.":
            resultado = await postar_meta(context, f"{modalidade} de {DIAS[dia.weekday()]}", item, log)
            sucesso = resultado is not False and sucesso

    await log.enviar_log(context)
    return sucesso
