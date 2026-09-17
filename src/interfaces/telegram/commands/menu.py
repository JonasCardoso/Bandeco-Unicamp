"""Comandos de consulta de cardápio, horários e preços."""

import asyncio

from telegram import Update
from telegram.ext import CallbackContext

from integrations.unicamp.price_client import obter_valores_refeicao
from integrations.unicamp.schedule_client import horario_funcionamento
from interfaces.telegram.logging import Log
from interfaces.telegram.messaging import mandar_mensagem
from interfaces.telegram.screens import enviar


async def _hoje(update, context, refeicao):
    from integrations.firebase.user_repository import get_firebase
    from interfaces.telegram.navigation import cardapio
    from modules.menu.view import hoje

    if update.effective_chat.type != "private":
        await mandar_mensagem(
            context, update.effective_chat.id, "Abra o bot no privado para consultar o cardápio.", parse_mode=None
        )
        return
    dados = await asyncio.to_thread(get_firebase().pegar_usuario, update.effective_chat.id)
    modalidade = "vegano" if dados and dados.get("vegano") and not dados.get("tradicional") else "tradicional"
    await cardapio(update, context, refeicao, hoje(), modalidade)


async def cafe(update: Update, context: CallbackContext):
    await _hoje(update, context, "cafe")


async def almoco(update: Update, context: CallbackContext):
    await _hoje(update, context, "almoco")


async def jantar(update: Update, context: CallbackContext):
    await _hoje(update, context, "jantar")


async def preco(update: Update, context: CallbackContext):
    """Retorna a tabela de valores das refeições da Prefeitura Universitária."""
    resultado = await asyncio.to_thread(obter_valores_refeicao)
    if resultado is None:
        await mandar_mensagem(
            context, update.effective_chat.id, "Não foi possível consultar os valores. Tente novamente mais tarde."
        )
        return
    texto = resultado
    await mandar_mensagem(context, update.effective_chat.id, texto, parse_mode="HTML")


async def horario(update: Update, context: CallbackContext):
    log = Log()
    horarios = await asyncio.to_thread(horario_funcionamento)
    if horarios is None:
        log.error(
            "Não foi possível consultar o horário",
            component="telegram.menu",
            event="schedule_fetch_failed",
            context={"chat_id": update.effective_chat.id, "username": update.effective_chat.username},
        )
        await log.enviar_log(context)
        return

    await enviar(
        context.bot, update.effective_chat.id, "Horários de funcionamento\n\n" + horarios, destacar_titulo=True
    )
