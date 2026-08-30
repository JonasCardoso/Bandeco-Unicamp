"""Comandos de captura das câmeras dos restaurantes."""

import asyncio
from functools import lru_cache

from telegram import Update
from telegram.ext import CallbackContext

from core.config import get_cam_ra, get_cam_rs, get_cam_ru_a, get_cam_ru_b
from interfaces.telegram.messaging import mandar_imagem
from modules.cameras.service import Cam


@lru_cache(maxsize=1)
def get_cam() -> Cam:
    """Mantém o throttling das câmeras sem criar objeto durante import."""
    return Cam()


async def ru(update: Update, context: CallbackContext):
    await asyncio.to_thread(get_cam().pegar_imagem, "ru")
    await mandar_imagem(context, update.effective_chat.id, get_cam_ru_a())
    await mandar_imagem(context, update.effective_chat.id, get_cam_ru_b())


async def ra(update: Update, context: CallbackContext):
    await asyncio.to_thread(get_cam().pegar_imagem, "ra")
    await mandar_imagem(context, update.effective_chat.id, get_cam_ra())


async def rs(update: Update, context: CallbackContext):
    await asyncio.to_thread(get_cam().pegar_imagem, "rs")
    await mandar_imagem(context, update.effective_chat.id, get_cam_rs())
