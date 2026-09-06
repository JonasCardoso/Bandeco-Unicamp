"""Comando de consulta de saldo."""

import time

from telegram import ForceReply, Update
from telegram.ext import CallbackContext

from interfaces.telegram.messaging import mandar_mensagem
from interfaces.telegram.screens import enviar


async def saldo(update: Update, context: CallbackContext):
    if update.effective_chat.type != "private":
        await mandar_mensagem(
            context, update.effective_chat.id, "Abra o bot no privado para consultar saldo.", parse_mode=None
        )
        return
    context.user_data["saldo_ate"] = time.monotonic() + 300
    await enviar(
        context.bot,
        update.effective_chat.id,
        'Consulta de saldo\n\nDigite seu RA e a senha da DAC no formato "<RA> <Senha>". '
        "Exemplo: 123456 abcdefghi\n\nVocê tem cinco minutos. Use /cancelar para encerrar.",
        markup=ForceReply(),
        destacar_titulo=True,
    )


async def cancelar(update: Update, context: CallbackContext):
    context.user_data.pop("saldo_ate", None)
    await mandar_mensagem(
        context, update.effective_chat.id, "Consulta cancelada. Use /menu para voltar.", parse_mode=None
    )
