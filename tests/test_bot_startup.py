"""Regressões do pré-carregamento nutricional no startup do bot."""

import importlib
import logging
from unittest.mock import MagicMock

import pytest


def _bot():
    return importlib.import_module("bot")


def _configurar_startup(monkeypatch, bot):
    monkeypatch.setattr(bot, "validar_env_vars", lambda: [])
    monkeypatch.setattr(bot, "log_env_validation", lambda _: None)
    monkeypatch.setattr(bot, "configurar_runtime", lambda: None)
    monkeypatch.setattr(bot, "get_firebase", lambda: object())
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
    monkeypatch.setattr(bot, "get_firebase", lambda: eventos.append("firebase") or object())
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

    with caplog.at_level(logging.INFO):
        bot.main()

    assert eventos == ["firebase", "application", "polling"]


def test_falha_do_firebase_impede_pipeline(monkeypatch):
    bot = _bot()
    _configurar_startup(monkeypatch, bot)

    def falhar():
        raise ValueError("credenciais inválidas")

    monkeypatch.setattr(bot, "get_firebase", falhar)
    with pytest.raises(SystemExit) as erro:
        bot.main()
    assert erro.value.code == 1
