"""Regressões do pré-carregamento nutricional no startup do bot."""

import importlib
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


def _bot():
    return importlib.import_module("bot")


def _configurar_startup(monkeypatch, bot):
    monkeypatch.setattr(bot, "validar_env_vars", lambda: [])
    monkeypatch.setattr(bot, "log_env_validation", lambda _: None)
    monkeypatch.setattr(bot, "get_token_bot_telegram", lambda: "token")
    monkeypatch.setattr(bot, "get_horario_cafe", lambda: 7)
    monkeypatch.setattr(bot, "get_horario_almoco", lambda: 12)
    monkeypatch.setattr(bot, "get_horario_jantar", lambda: 19)
    monkeypatch.setattr(bot, "CommandHandler", lambda *args, **kwargs: object())
    monkeypatch.setattr(bot, "MessageHandler", lambda *args, **kwargs: object())


def test_pipeline_carrega_antes_do_polling(monkeypatch, caplog):
    bot = _bot()
    _configurar_startup(monkeypatch, bot)
    eventos = []
    application = MagicMock()
    application.run_polling.side_effect = lambda: eventos.append("polling")

    class Builder:
        def token(self, _):
            return self

        def build(self):
            eventos.append("application")
            return application

    class Application:
        @staticmethod
        def builder():
            return Builder()

    monkeypatch.setattr(bot, "Application", Application)
    monkeypatch.setattr(
        bot,
        "inicializar_pipeline_nutricional",
        lambda: eventos.append("pipeline") or SimpleNamespace(device="cpu"),
    )

    with caplog.at_level(logging.INFO):
        bot.main()

    assert eventos == ["pipeline", "application", "polling"]
    assert "Pipeline nutricional pronto" in caplog.text


def test_falha_do_pipeline_impede_bot_de_iniciar(monkeypatch, caplog):
    bot = _bot()
    _configurar_startup(monkeypatch, bot)

    def falhar():
        raise RuntimeError("modelo indisponível")

    monkeypatch.setattr(bot, "inicializar_pipeline_nutricional", falhar)
    monkeypatch.setattr(
        bot.Application,
        "builder",
        lambda: pytest.fail("Application não deveria ser construída"),
    )

    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as erro:
        bot.main()

    assert erro.value.code == 1
    assert "o bot não será iniciado" in caplog.text
