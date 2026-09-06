"""Registro central dos handlers Telegram."""

import logging

from telegram import BotCommand
from telegram.error import TelegramError
from telegram.ext import CallbackQueryHandler, ChatMemberHandler, filters

from interfaces.telegram.commands.balance import cancelar, saldo
from interfaces.telegram.commands.cameras import ra, rs, ru
from interfaces.telegram.commands.general import ajuda, contato, mensagem, mensagem_contato
from interfaces.telegram.commands.menu import almoco, cafe, horario, jantar, preco
from interfaces.telegram.commands.preferences import (
    desativar,
    modalidade,
    notificacao,
    reset_contato,
    reset_modalidade,
    reset_notificacao,
    start,
)
from interfaces.telegram.commands.social import facebook, instagram, twitter
from interfaces.telegram.handlers import tabela
from interfaces.telegram.logging import tratar_erro_aplicacao
from interfaces.telegram.navigation import bloqueio, callback, excluir, menu


def register_handlers(application, command_handler, message_handler) -> None:
    """Adiciona todos os comandos e listeners à aplicação Telegram."""
    comandos = (
        ("start", start),
        ("menu", menu),
        ("excluir", excluir),
        ("cancelar", cancelar),
        ("cafe", cafe),
        ("almoco", almoco),
        ("jantar", jantar),
        ("modalidade", modalidade),
        ("notificacao", notificacao),
        ("horario", horario),
        ("saldo", saldo),
        ("contato", contato),
        ("ru", ru),
        ("ra", ra),
        ("rs", rs),
        ("tabela", tabela),
        ("preco", preco),
        ("twitter", twitter),
        ("instagram", instagram),
        ("facebook", facebook),
        ("desativar", desativar),
        ("reset_modalidade", reset_modalidade),
        ("reset_notificacao", reset_notificacao),
        ("reset_contato", reset_contato),
        ("ajuda", ajuda),
    )
    for nome, handler in comandos:
        application.add_handler(command_handler(nome, handler))
    application.add_handler(CallbackQueryHandler(callback))
    application.add_handler(ChatMemberHandler(bloqueio, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(message_handler(filters.TEXT & ~filters.COMMAND, mensagem))
    application.add_handler(message_handler(filters.CONTACT, mensagem_contato))
    application.add_error_handler(tratar_erro_aplicacao)


async def configurar_comandos(application):
    try:
        await application.bot.set_my_commands(
            [
                BotCommand(nome, descricao)
                for nome, descricao in [
                    ("menu", "Abrir painel"),
                    ("cafe", "Café de hoje"),
                    ("almoco", "Almoço de hoje"),
                    ("jantar", "Jantar de hoje"),
                    ("notificacao", "Configurar notificações"),
                    ("saldo", "Consultar saldo no privado"),
                    ("ajuda", "Todos os comandos"),
                    ("cancelar", "Cancelar consulta"),
                    ("excluir", "Excluir cadastro"),
                ]
            ]
        )
    except TelegramError:
        logging.getLogger(__name__).warning("Não foi possível atualizar o menu de comandos; polling continuará.")
