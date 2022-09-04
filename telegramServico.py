import pathlib
from telegram import ReplyKeyboardMarkup
from telegram.ext import CallbackContext


def mandarMensagem(context: CallbackContext, id, texto, forceReply=None, replyMessage=None):
    try:
        context.bot.send_message(chat_id=id, parse_mode="Markdown", text=texto, reply_markup=forceReply,
                                 reply_to_message_id=replyMessage)
    except:
        None


def deletarMensagem(context: CallbackContext, id, idMessage):
    try:
        context.bot.delete_message(chat_id=id, message_id=idMessage)
    except:
        None


def mandarMensagemTeclado(context: CallbackContext, id, texto, buttons):
    try:
        context.bot.send_message(chat_id=id, parse_mode="Markdown", text=texto,
                                 reply_markup=ReplyKeyboardMarkup(buttons))
    except:
        None


def mandarImagem(context: CallbackContext, id, imagem):
    try:
        context.bot.send_photo(chat_id=id, parse_mode="Markdown",
                               photo=open(f'{pathlib.Path().resolve()}/{imagem}.jpg', 'rb'))
    except:
        None
