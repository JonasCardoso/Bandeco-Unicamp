import pathlib
from telegram import ReplyKeyboardMarkup
from telegram.ext import CallbackContext


async def mandar_mensagem(context: CallbackContext, chat_id, texto, reply_markup=None, reply_to_message_id=None):
    try:
        await context.bot.send_message(chat_id=chat_id, parse_mode="Markdown", text=texto, reply_markup=reply_markup,
                                       reply_to_message_id=reply_to_message_id)
    except:
        None


async def deletar_mensagem(context: CallbackContext, chat_id, message_id):
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        None


async def mandar_mensagem_teclado(context: CallbackContext, chat_id, texto, buttons):
    try:
        await context.bot.send_message(chat_id=chat_id, parse_mode="Markdown", text=texto,
                                       reply_markup=ReplyKeyboardMarkup(buttons))
    except:
        None


async def mandar_imagem(context: CallbackContext, chat_id, imagem):
    try:
        await context.bot.send_photo(chat_id=chat_id, parse_mode="Markdown",
                                     photo=open(f'{pathlib.Path().resolve()}/{imagem}.jpg', 'rb'))
    except:
        None
