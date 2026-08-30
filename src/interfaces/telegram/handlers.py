"""Handler Telegram para geração da tabela nutricional."""

import asyncio

from telegram import Update
from telegram.ext import CallbackContext

from core.config import get_bot_username
from interfaces.telegram.messaging import mandar_imagem, mandar_mensagem
from modules.nutrition.pipeline import gerar_tabela_nutricional


async def tabela(update: Update, context: CallbackContext):
    resposta = update.message.reply_to_message
    remetente = getattr(resposta, "from_user", None) if resposta is not None else None
    if resposta is not None and get_bot_username() == getattr(remetente, "username", None):
        message = resposta.text
        if message is not None and any(word in message for word in ["Almoço", "Jantar", "Café da manhã"]):
            imagem = await asyncio.to_thread(gerar_tabela_nutricional, resposta.text)
            if imagem is not None:
                await mandar_imagem(context, update.effective_chat.id, imagem, resposta.message_id)
                return
            else:
                await mandar_mensagem(
                    context,
                    update.effective_chat.id,
                    "Nenhum prato identificado no cardápio para gerar a tabela nutricional. "
                    "Tente novamente mais tarde.",
                )
                return

    await mandar_mensagem(
        context, update.effective_chat.id, "Use o comando /tabela respondendo a uma mensagem do cardápio."
    )
