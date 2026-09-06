"""Handler Telegram para geração da tabela nutricional."""

from telegram import Update
from telegram.ext import CallbackContext

from core.config import get_bot_username
from interfaces.telegram.messaging import mandar_mensagem
from modules.nutrition.pipeline import gerar_tabela_nutricional


async def tabela(update: Update, context: CallbackContext):
    if update.message is None:
        return
    resposta = update.message.reply_to_message
    remetente = getattr(resposta, "from_user", None) if resposta is not None else None
    if resposta is not None and get_bot_username() == getattr(remetente, "username", None):
        message = resposta.text
        if message is not None and any(word in message for word in ["Almoço", "Jantar", "Café da manhã"]):
            from interfaces.telegram.nutrition_tasks import processar
            from interfaces.telegram.screens import enviar

            chat_id = update.effective_chat.id
            ativos = context.bot_data.setdefault("nutrition_users", set())
            if chat_id in ativos:
                return
            ativos.add(chat_id)
            try:
                status = await enviar(context.bot, chat_id, "Preparando tabela nutricional…")
            except BaseException:
                ativos.discard(chat_id)
                raise
            if status.erro:
                ativos.discard(chat_id)
                return

            async def trabalho():
                try:
                    await processar(
                        context, chat_id, message, status.message_id, gerar_tabela_nutricional, resposta.message_id
                    )
                finally:
                    ativos.discard(chat_id)

            corrotina = trabalho()
            try:
                context.application.create_task(corrotina, update=update)
            except BaseException:
                corrotina.close()
                ativos.discard(chat_id)
                raise
            return

    await mandar_mensagem(
        context, update.effective_chat.id, "Use o comando /tabela respondendo a uma mensagem do cardápio."
    )
