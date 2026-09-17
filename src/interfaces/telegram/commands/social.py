"""Comandos com links das redes sociais."""

from telegram import Update
from telegram.ext import CallbackContext

from interfaces.telegram.messaging import mandar_mensagem


async def twitter(update: Update, context: CallbackContext):
    await mandar_mensagem(
        context, update.effective_chat.id, "Atualizações diárias no twitter: https://x.com/bandecounicamp"
    )


async def instagram(update: Update, context: CallbackContext):
    await mandar_mensagem(
        context, update.effective_chat.id, "Atualizações diárias no instagram: https://instagram.com/bandecounicamp"
    )


async def facebook(update: Update, context: CallbackContext):
    await mandar_mensagem(
        context, update.effective_chat.id, "Atualizações diárias no facebook: https://facebook.com/bandecounicamp"
    )
