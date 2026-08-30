"""Regressões dos handlers Telegram."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from interfaces.telegram import handlers as comando


class Reply:
    def __init__(self, username, text):
        self.from_user = SimpleNamespace(username=username)
        self.text = text
        self.message_id = 42


@pytest.mark.asyncio
async def test_tabela_aceita_username_configurado(monkeypatch):
    update = MagicMock()
    update.effective_chat.id = 123
    update.message.reply_to_message = Reply("bot_producao", "Almoço de Segunda-feira\nArroz e feijão")
    context = MagicMock()
    enviar = AsyncMock()
    monkeypatch.setattr(comando, "get_bot_username", lambda: "bot_producao")
    monkeypatch.setattr(comando, "gerar_tabela_nutricional", lambda _: "cache/tabela")
    monkeypatch.setattr(comando, "mandar_imagem", enviar)

    await comando.tabela(update, context)

    enviar.assert_awaited_once_with(context, 123, "cache/tabela", 42)
