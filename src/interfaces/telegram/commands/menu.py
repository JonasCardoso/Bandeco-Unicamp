"""Comandos de consulta de cardápio, horários e preços."""

import asyncio

from telegram import Update
from telegram.ext import CallbackContext

from core.constants import DIAS
from integrations.unicamp.price_client import obter_valores_refeicao
from integrations.unicamp.schedule_client import horario_funcionamento
from interfaces.telegram.keyboards import teclado_dias_semana
from interfaces.telegram.logging import Log
from interfaces.telegram.messaging import mandar_mensagem, mandar_mensagem_teclado


async def cafe(update: Update, context: CallbackContext):
    periodo = "Café da manhã"
    buttons = teclado_dias_semana(periodo, DIAS)
    await mandar_mensagem_teclado(context, update.effective_chat.id, "Selecione o dia da semana", buttons)


async def almoco(update: Update, context: CallbackContext):
    periodo = "Almoço"
    buttons = teclado_dias_semana(periodo, DIAS)
    await mandar_mensagem_teclado(context, update.effective_chat.id, "Selecione o dia da semana", buttons)


async def jantar(update: Update, context: CallbackContext):
    periodo = "Jantar"
    buttons = teclado_dias_semana(periodo, DIAS)
    await mandar_mensagem_teclado(context, update.effective_chat.id, "Selecione o dia da semana", buttons)


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

    await mandar_mensagem(context, update.effective_chat.id, horarios)
