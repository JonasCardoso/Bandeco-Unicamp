"""Comandos de cadastro e preferências do usuário."""

from telegram import Update
from telegram.ext import CallbackContext

from integrations.firebase.user_repository import get_firebase
from interfaces.telegram.keyboards import teclado_modalidades, teclado_notificacao
from interfaces.telegram.logging import Log
from interfaces.telegram.messaging import mandar_mensagem, mandar_mensagem_teclado


async def start(update: Update, context: CallbackContext):
    log = Log()
    if get_firebase().criar_usuario(update.effective_chat.id):
        await mandar_mensagem(
            context,
            update.effective_chat.id,
            "Olá Unicamper, seja bem-vindo ao Bandeco Unicamp, consulte "
            "e receba os cardápios diários da universidade!!!",
        )
        return
    else:
        await mandar_mensagem(
            context,
            update.effective_chat.id,
            "Olá Unicamper, houve algum problema na base de dados, use /start novamente!!!",
        )
        log.adicionar_log(
            f"start - {update.effective_chat.id} - {update.effective_chat.full_name} - "
            f"{update.effective_chat.username} - Não foi possível criar o usuário"
        )
        await log.enviar_log(context)


async def modalidade(update: Update, context: CallbackContext):
    log = Log()
    dados = get_firebase().pegar_usuario(update.effective_chat.id)
    if dados:
        buttons = teclado_modalidades(dados)
        await mandar_mensagem_teclado(
            context, update.effective_chat.id, "Ative ou inative de acordo com sua preferência", buttons
        )
        return

    log.adicionar_log(
        f"modalidade - {update.effective_chat.id} - {update.effective_chat.full_name} - "
        f"{update.effective_chat.username} - Não foi possível pegar o usuário"
    )
    await log.enviar_log(context)


async def notificacao(update: Update, context: CallbackContext):
    log = Log()
    dados = get_firebase().pegar_usuario(update.effective_chat.id)
    if dados:
        buttons = teclado_notificacao(dados)
        await mandar_mensagem_teclado(
            context, update.effective_chat.id, "Ative ou inative de acordo com sua preferência", buttons
        )
        return

    log.adicionar_log(
        f"notificacao - {update.effective_chat.id} - {update.effective_chat.full_name} - "
        f"{update.effective_chat.username} - Não foi possível pegar o usuário"
    )
    await log.enviar_log(context)


async def desativar(update: Update, context: CallbackContext):
    """Zera TODOS os dados do usuário (modalidade + notificações + contato)."""
    log = Log()
    dados = {"tradicional": 0, "vegano": 0, "cafe": 0, "almoco": 0, "jantar": 0, "telefone": 0}
    if get_firebase().atualizar_usuario(dados, update.effective_chat.id):
        await mandar_mensagem(context, update.effective_chat.id, "Olá Unicamper, TODOS os seus dados foram apagados!!!")
        return

    log.adicionar_log(
        f"desativar - {update.effective_chat.id} - {update.effective_chat.full_name} - "
        f"{update.effective_chat.username} - Não foi possível apagar os dados do usuário"
    )
    await log.enviar_log(context)


async def reset_modalidade(update: Update, context: CallbackContext):
    """Zera apenas as preferências de modalidade (tradicional/vegano)."""
    log = Log()
    dados = {"tradicional": 0, "vegano": 0}
    if get_firebase().atualizar_usuario(dados, update.effective_chat.id):
        await mandar_mensagem(context, update.effective_chat.id, "Suas preferências de modalidade foram apagadas!!!")
        return

    log.adicionar_log(
        f"reset_modalidade - {update.effective_chat.id} - {update.effective_chat.full_name} - "
        f"{update.effective_chat.username} - Não foi possível apagar a modalidade"
    )
    await log.enviar_log(context)


async def reset_notificacao(update: Update, context: CallbackContext):
    """Zera apenas as preferências de notificação (cafe/almoço/jantar)."""
    log = Log()
    dados = {"cafe": 0, "almoco": 0, "jantar": 0}
    if get_firebase().atualizar_usuario(dados, update.effective_chat.id):
        await mandar_mensagem(context, update.effective_chat.id, "Suas notificações foram desativadas!!!")
        return

    log.adicionar_log(
        f"reset_notificacao - {update.effective_chat.id} - {update.effective_chat.full_name} - "
        f"{update.effective_chat.username} - Não foi possível apagar as notificações"
    )
    await log.enviar_log(context)


async def reset_contato(update: Update, context: CallbackContext):
    """Zera apenas o contato cadastrado."""
    log = Log()
    dados = {"telefone": 0}
    if get_firebase().atualizar_usuario(dados, update.effective_chat.id):
        await mandar_mensagem(context, update.effective_chat.id, "Seu contato foi removido!!!")
        return

    log.adicionar_log(
        f"reset_contato - {update.effective_chat.id} - {update.effective_chat.full_name} - "
        f"{update.effective_chat.username} - Não foi possível apagar o contato"
    )
    await log.enviar_log(context)
