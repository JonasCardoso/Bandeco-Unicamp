"""Serviços resilientes de comunicação com a API do Telegram."""

from __future__ import annotations

import logging
import pathlib

from telegram import ReplyKeyboardMarkup
from telegram.error import TelegramError
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)


async def mandar_mensagem(
    context: CallbackContext,
    chat_id,
    texto,
    reply_markup=None,
    reply_to_message_id=None,
    parse_mode="Markdown",
) -> bool:
    """Envia texto e informa se a API confirmou a operação."""
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            parse_mode=parse_mode,
            text=texto,
            reply_markup=reply_markup,
            reply_to_message_id=reply_to_message_id,
        )
        return True
    except TelegramError:
        logger.warning("Telegram recusou mensagem para o chat %s.", chat_id, exc_info=True)
    except Exception:
        logger.exception("Falha inesperada ao enviar mensagem para o chat %s.", chat_id)
    return False


async def deletar_mensagem(context: CallbackContext, chat_id, message_id) -> bool:
    """Remove uma mensagem e informa se a API confirmou a operação."""
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except TelegramError:
        logger.warning("Telegram recusou exclusão no chat %s.", chat_id, exc_info=True)
    except Exception:
        logger.exception("Falha inesperada ao excluir mensagem no chat %s.", chat_id)
    return False


async def mandar_mensagem_teclado(context: CallbackContext, chat_id, texto, buttons) -> bool:
    """Envia uma mensagem com teclado de resposta."""
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            parse_mode="Markdown",
            text=texto,
            reply_markup=ReplyKeyboardMarkup(buttons),
        )
        return True
    except TelegramError:
        logger.warning("Telegram recusou teclado para o chat %s.", chat_id, exc_info=True)
    except Exception:
        logger.exception("Falha inesperada ao enviar teclado para o chat %s.", chat_id)
    return False


async def mandar_imagem(context: CallbackContext, chat_id, imagem, reply_to_message_id=None) -> bool:
    """Envia um JPEG do diretório de trabalho sem propagar falhas recuperáveis."""
    caminho = pathlib.Path(pathlib.Path().resolve()) / f"{imagem}.jpg"
    try:
        with caminho.open("rb") as arquivo:
            await context.bot.send_photo(
                chat_id=chat_id,
                parse_mode="Markdown",
                photo=arquivo,
                reply_to_message_id=reply_to_message_id,
            )
        return True
    except OSError:
        logger.warning("Imagem %s indisponível para o chat %s.", caminho.name, chat_id, exc_info=True)
    except TelegramError:
        logger.warning("Telegram recusou imagem para o chat %s.", chat_id, exc_info=True)
    except Exception:
        logger.exception("Falha inesperada ao enviar imagem para o chat %s.", chat_id)
    return False
