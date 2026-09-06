"""Entrega Telegram com limites conservadores e falhas classificadas."""

import asyncio
import time

from telegram.error import Forbidden, NetworkError, RetryAfter, TelegramError, TimedOut

from interfaces.telegram.formatting import titulo_em_negrito
from interfaces.telegram.screens import ResultadoEnvio


class DeliverySender:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.ultimo = 0.0
        self.chats = {}

    async def enviar(self, bot, chat_id, texto, markup=None, silencioso=False, destacar_titulo=False):
        entidades = {"entities": titulo_em_negrito(texto)} if destacar_titulo else {}
        for tentativa in range(3):
            async with self.lock:
                agora = time.monotonic()
                espera = max(0, self.ultimo + 0.05 - agora, self.chats.get(str(chat_id), 0) + 1.1 - agora)
                if espera:
                    await asyncio.sleep(espera)
                self.ultimo = time.monotonic()
                self.chats = {ch: t for ch, t in self.chats.items() if self.ultimo - t < 2}
                self.chats[str(chat_id)] = self.ultimo
            try:
                mensagem = await bot.send_message(
                    chat_id=chat_id,
                    text=texto,
                    parse_mode=None,
                    reply_markup=markup,
                    disable_notification=silencioso,
                    **entidades,
                )
                return ResultadoEnvio(mensagem.message_id)
            except RetryAfter as erro:
                segundos = (
                    erro.retry_after.total_seconds() if hasattr(erro.retry_after, "total_seconds") else erro.retry_after
                )
                if tentativa == 2 or segundos > 60:
                    return ResultadoEnvio(erro="limite")
                await asyncio.sleep(segundos + 0.1)
            except Forbidden:
                return ResultadoEnvio(erro="bloqueado")
            except (TimedOut, NetworkError):
                # O servidor pode ter aceitado a mensagem antes da conexão cair.
                return ResultadoEnvio(erro="incerto")
            except TelegramError:
                return ResultadoEnvio(erro="falha")
        return ResultadoEnvio(erro="limite")
