"""Serviços de comunicação com a API do Telegram.

Este módulo fornece funções assíncronas para envio de mensagens e imagens
para o bot do Telegram, incluindo suporte para teclados interativos.
"""

import pathlib

from telegram import ReplyKeyboardMarkup
from telegram.ext import CallbackContext


async def mandar_mensagem(context: CallbackContext, chat_id, texto, reply_markup=None,
                          reply_to_message_id=None, parse_mode="Markdown"):
    """Envia uma mensagem de texto para um chat.

    Args:
        context: Contexto do bot Telegram.
        chat_id: ID do chat destino.
        texto: Texto da mensagem.
        reply_markup: Teclado de resposta opcional.
        reply_to_message_id: ID da mensagem para responder (opcional).
        parse_mode: Modo de formatação (Markdown ou HTML).
    """
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            parse_mode=parse_mode,
            text=texto,
            reply_markup=reply_markup,
            reply_to_message_id=reply_to_message_id,
        )
    except Exception as e:
        print(f"[ERROR] Telegram - mandar_mensagem({chat_id}): {e}")


async def deletar_mensagem(context: CallbackContext, chat_id, message_id):
    """Deleta uma mensagem de um chat.

    Args:
        context: Contexto do bot Telegram.
        chat_id: ID do chat destino.
        message_id: ID da mensagem a ser deletada.
    """
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"[ERROR] Telegram - deletar_mensagem({chat_id}, {message_id}): {e}")


async def mandar_mensagem_teclado(context: CallbackContext, chat_id, texto, buttons):
    """Envia uma mensagem com teclado interativo.

    Args:
        context: Contexto do bot Telegram.
        chat_id: ID do chat destino.
        texto: Texto da mensagem.
        buttons: Lista de botões para o teclado.
    """
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            parse_mode="Markdown",
            text=texto,
            reply_markup=ReplyKeyboardMarkup(buttons),
        )
    except Exception as e:
        print(f"[ERROR] Telegram - mandar_mensagem_teclado({chat_id}): {e}")


async def mandar_imagem(context: CallbackContext, chat_id, imagem, reply_to_message_id=None):
    """Envia uma imagem para um chat.

    Args:
        context: Contexto do bot Telegram.
        chat_id: ID do chat destino.
        imagem: Nome do arquivo da imagem (sem extensão).
        reply_to_message_id: ID da mensagem para responder (opcional).
    """
    try:
        with open(f'{pathlib.Path().resolve()}/{imagem}.jpg', 'rb') as f:
            await context.bot.send_photo(
                chat_id=chat_id,
                parse_mode="Markdown",
                photo=f,
                reply_to_message_id=reply_to_message_id,
            )
    except Exception as e:
        print(f"[ERROR] Telegram - mandar_imagem({chat_id}, {imagem}): {e}")
