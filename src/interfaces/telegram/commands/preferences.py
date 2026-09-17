"""Comandos de cadastro e preferências do usuário."""

import asyncio

from telegram import Update
from telegram.ext import CallbackContext

from integrations.firebase.user_repository import get_firebase
from interfaces.telegram.logging import Log
from interfaces.telegram.messaging import mandar_mensagem


async def start(update: Update, context: CallbackContext):
    from interfaces.telegram.navigation import iniciar

    await iniciar(update, context)


async def modalidade(update: Update, context: CallbackContext):
    from interfaces.telegram.navigation import preferencias

    await preferencias(update, context)


async def notificacao(update: Update, context: CallbackContext):
    from interfaces.telegram.navigation import preferencias

    await preferencias(update, context)


async def desativar(update: Update, context: CallbackContext):
    """Zera TODOS os dados do usuário (modalidade + notificações + contato)."""
    log = Log()
    dados = {"tradicional": 0, "vegano": 0, "cafe": 0, "almoco": 0, "jantar": 0, "telefone": 0}
    if await asyncio.to_thread(get_firebase().atualizar_usuario, dados, update.effective_chat.id):
        await mandar_mensagem(
            context,
            update.effective_chat.id,
            "Preferências, notificações e contato foram desativados. Para excluir seu cadastro, use /excluir.",
        )
        return

    log.adicionar_log(
        f"desativar - {update.effective_chat.id} - {update.effective_chat.full_name} - "
        f"{update.effective_chat.username} - Não foi possível apagar os dados do usuário"
    )
    await log.enviar_log(context)


async def reset_modalidade(update: Update, context: CallbackContext):
    """Zera apenas as preferências de modalidade (tradicional/vegano)."""
    log = Log()
    dados = {"tradicional": 0, "vegano": 0}
    if await asyncio.to_thread(get_firebase().atualizar_usuario, dados, update.effective_chat.id):
        await mandar_mensagem(context, update.effective_chat.id, "Suas preferências de modalidade foram apagadas!!!")
        return

    log.adicionar_log(
        f"reset_modalidade - {update.effective_chat.id} - {update.effective_chat.full_name} - "
        f"{update.effective_chat.username} - Não foi possível apagar a modalidade"
    )
    await log.enviar_log(context)


async def reset_notificacao(update: Update, context: CallbackContext):
    """Zera apenas as preferências de notificação (cafe/almoço/jantar)."""
    log = Log()
    dados = {"cafe": 0, "almoco": 0, "jantar": 0}
    if await asyncio.to_thread(get_firebase().atualizar_usuario, dados, update.effective_chat.id):
        await mandar_mensagem(context, update.effective_chat.id, "Suas notificações foram desativadas!!!")
        return

    log.adicionar_log(
        f"reset_notificacao - {update.effective_chat.id} - {update.effective_chat.full_name} - "
        f"{update.effective_chat.username} - Não foi possível apagar as notificações"
    )
    await log.enviar_log(context)


async def reset_contato(update: Update, context: CallbackContext):
    """Zera apenas o contato cadastrado."""
    log = Log()
    dados = {"telefone": 0}
    if await asyncio.to_thread(get_firebase().atualizar_usuario, dados, update.effective_chat.id):
        await mandar_mensagem(context, update.effective_chat.id, "Seu contato foi removido!!!")
        return

    log.adicionar_log(
        f"reset_contato - {update.effective_chat.id} - {update.effective_chat.full_name} - "
        f"{update.effective_chat.username} - Não foi possível apagar o contato"
    )
    await log.enviar_log(context)
