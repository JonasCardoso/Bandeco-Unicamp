"""Comando de consulta de saldo."""

from telegram import ForceReply, Update
from telegram.ext import CallbackContext

from interfaces.telegram.messaging import mandar_mensagem


async def saldo(update: Update, context: CallbackContext):
    await mandar_mensagem(
        context,
        update.effective_chat.id,
        'Digite seu RA e a senha da DAC no formato "<RA> <Senha>" para consultar seu saldo. Exemplo: 123456 abcdefghi',
        reply_markup=ForceReply(),
    )
