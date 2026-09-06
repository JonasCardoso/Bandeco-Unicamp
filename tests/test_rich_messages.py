"""Piloto isolado e opt-in, sem chamadas reais à API."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

from telegram.error import BadRequest

from interfaces.telegram import rich_messages as rich
from modules.menu.view import adaptar


async def test_piloto_desligado_nao_chama_api(monkeypatch):
    monkeypatch.setattr(
        rich, "get_settings", lambda: SimpleNamespace(telegram_rich_enabled=False, telegram_rich_chat_ids="7")
    )
    bot = SimpleNamespace(do_api_request=AsyncMock())
    assert not await rich.tentar(bot, 7, "html")
    bot.do_api_request.assert_not_awaited()


async def test_piloto_exige_lista_de_chats_e_fallback(monkeypatch):
    monkeypatch.setattr(
        rich, "get_settings", lambda: SimpleNamespace(telegram_rich_enabled=True, telegram_rich_chat_ids="7")
    )
    bot = SimpleNamespace(do_api_request=AsyncMock(side_effect=BadRequest("Unsupported method")))
    assert not await rich.tentar(bot, 8, "html")
    bot.do_api_request.assert_not_awaited()
    assert not await rich.tentar(bot, 7, "html", message_id=9)
    assert bot.do_api_request.call_args.args == ("editMessageText",)
    assert bot.do_api_request.call_args.kwargs["api_kwargs"]["rich_message"] == {"html": "html"}


def test_html_escapa_fonte_e_oferece_tabela_recolhivel():
    item = adaptar(["<script>&"] * 5, date(2026, 9, 6), "cafe", "tradicional")
    assert "<script>" not in rich.cardapio_html(item)
    html = rich.tabela_html([["Nome", "kcal"], ["Arroz & feijão", "123"]])
    assert "<details>" in html and "<table" in html and "&amp;" in html
    ausente = adaptar(None, date(2026, 9, 6), "almoco", "vegano")
    assert 'type="disabled"' in rich.cardapio_html(ausente)
