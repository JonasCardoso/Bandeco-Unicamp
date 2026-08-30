"""Registro central dos handlers Telegram."""

from telegram.ext import filters

from interfaces.telegram.commands.balance import saldo
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


def register_handlers(application, command_handler, message_handler) -> None:
    """Adiciona todos os comandos e listeners à aplicação Telegram."""
    comandos = (
        ("start", start),
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
    for nome, callback in comandos:
        application.add_handler(command_handler(nome, callback))
    application.add_handler(message_handler(filters.TEXT, mensagem))
    application.add_handler(message_handler(filters.CONTACT, mensagem_contato))
