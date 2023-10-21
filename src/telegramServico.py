import pathlib
from telegram import ReplyKeyboardMarkup
from telegram.ext import CallbackContext


async def mandarMensagem(context: CallbackContext, id, texto, forceReply=None, replyMessage=None):
    try:
        await context.bot.send_message(chat_id=id, parse_mode="Markdown", text=texto, reply_markup=forceReply,
                                       reply_to_message_id=replyMessage)
    except:
        None


async def deletarMensagem(context: CallbackContext, id, idMessage):
    try:
        await context.bot.delete_message(chat_id=id, message_id=idMessage)
    except:
        None


async def mandarMensagemTeclado(context: CallbackContext, id, texto, buttons):
    try:
        await context.bot.send_message(chat_id=id, parse_mode="Markdown", text=texto,
                                       reply_markup=ReplyKeyboardMarkup(buttons))
    except:
        None


async def mandarImagem(context: CallbackContext, id, imagem):
    try:
        await context.bot.send_photo(chat_id=id, parse_mode="Markdown",
                                     photo=open(f'{pathlib.Path().resolve()}/{imagem}.jpg', 'rb'))
    except:
        None
