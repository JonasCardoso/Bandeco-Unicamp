"""Persistência, reinícios e isolamento das rotinas de entrega."""

import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.error import Forbidden, RetryAfter, TimedOut

from integrations.firebase.delivery_repository import DeliveryRepository
from integrations.firebase.user_repository import Config
from interfaces.telegram.delivery import DeliverySender
from modules.menu.view import FUSO
from modules.notifications import service


class Reference:
    def __init__(self, data=None, path=()):
        self.data = {} if data is None else data
        self.path = path

    def child(self, key):
        return Reference(self.data, (*self.path, key))

    def transaction(self, fn):
        value = fn(self.data.get(self.path))
        self.data[self.path] = value
        return value

    def get(self):
        return self.data.get(self.path)


def test_cadastro_transacional_preserva_preferencias():
    ref = Reference()
    repo = Config(ref)
    assert repo.criar_usuario("7")
    novo = repo.pegar_usuario("7")
    assert [novo[x] for x in ("cafe", "almoco", "jantar")] == [0, 0, 0]
    ref.child("7").transaction(lambda _: {"vegano": 1, "almoco": 1})
    assert repo.criar_usuario("7")
    assert repo.pegar_usuario("7") == {"vegano": 1, "almoco": 1}


def test_preferencias_nao_recriam_excluido_e_onboarding_antigo_nao_reseta():
    repo = Config(Reference())
    assert not repo.definir_preferencias("7", {"almoco": 1})
    repo.ref.child("7").transaction(lambda _: {"almoco": 1})
    repo.definir_preferencias("7", {"almoco": 0}, cadastro=True)
    assert repo.pegar_usuario("7")["almoco"] == 1


def test_dias_sao_aditivos_e_repeticao_e_idempotente():
    repo = Config(Reference())
    repo.criar_usuario("7")
    repo.definir_dia("7", 0, False)
    repo.definir_dia("7", 0, False)
    assert repo.pegar_usuario("7")["dias"] == 126
    repo.definir_dia("7", 0, True)
    assert repo.pegar_usuario("7")["dias"] == 127


@pytest.mark.parametrize("estado", ["confirmado", "incerto", "bloqueado"])
def test_reinicio_nao_reenvia_entrega_terminal(estado):
    ref = Reference()
    repo = DeliveryRepository(ref)
    token = repo.reservar("7", "data_almoco_vegano")
    repo.concluir("7", "data_almoco_vegano", token, estado, 42)
    reiniciado = DeliveryRepository(ref)
    assert reiniciado.reservar("7", "data_almoco_vegano") is None


def test_reserva_concorrente_e_token_incorreto_nao_confirmam():
    repo = DeliveryRepository(Reference())
    token = repo.reservar("7", "dia")
    assert token
    assert repo.reservar("7", "dia") is None
    repo.concluir("7", "dia", "outro", "confirmado")
    assert repo.ref.child("7").child("dia").get()["estado"] == "enviando"


def test_reserva_abandonada_vira_incerta(monkeypatch):
    repo = DeliveryRepository(Reference())
    monkeypatch.setattr("integrations.firebase.delivery_repository.time.time", lambda: 10)
    repo.reservar("7", "dia")
    monkeypatch.setattr("integrations.firebase.delivery_repository.time.time", lambda: 700)
    assert repo.reservar("7", "dia") is None
    assert repo.ref.child("7").child("dia").get()["estado"] == "incerto"


async def test_retryafter_reenvia_mas_timeout_nao(monkeypatch):
    monkeypatch.setattr("interfaces.telegram.delivery.asyncio.sleep", AsyncMock())
    bot = SimpleNamespace(send_message=AsyncMock(side_effect=[RetryAfter(1), SimpleNamespace(message_id=42)]))
    assert (await DeliverySender().enviar(bot, 7, "texto")).message_id == 42
    assert bot.send_message.await_count == 2
    bot.send_message = AsyncMock(side_effect=TimedOut())
    assert (await DeliverySender().enviar(bot, 7, "texto")).erro == "incerto"
    bot.send_message.assert_awaited_once()


async def test_bloqueado_nao_repete():
    bot = SimpleNamespace(send_message=AsyncMock(side_effect=Forbidden("blocked")))
    assert (await DeliverySender().enviar(bot, 7, "texto")).erro == "bloqueado"
    bot.send_message.assert_awaited_once()


async def test_job_atrasado_usa_refeicao_e_isola_redes(monkeypatch):
    iniciado = asyncio.Event()
    liberar = asyncio.Event()

    async def rede(*args):
        iniciado.set()
        await liberar.wait()

    telegram = AsyncMock(return_value=True)
    monkeypatch.setattr(service, "comida", lambda _: ["arroz"] * 5)
    monkeypatch.setattr(service, "entregar_telegram", telegram)
    monkeypatch.setattr(service, "mensagem_cardapio_twitter", rede)
    monkeypatch.setattr(service, "mensagem_cardapio_meta", AsyncMock(side_effect=RuntimeError("indisponível")))
    estado = MagicMock()
    monkeypatch.setattr("shared.health.registrar_rotina", estado)
    context = SimpleNamespace(job=SimpleNamespace(data={"refeicao": "cafe"}))
    tarefa = asyncio.create_task(service.notificar_cardapio(context))
    await asyncio.wait_for(iniciado.wait(), 1)
    telegram.assert_awaited_once()
    assert telegram.call_args.args[-1] == "cafe"
    liberar.set()
    await tarefa
    assert estado.call_args.args[-1] == "parcial"


async def test_notificacao_respeita_preferencias_e_reinicio(monkeypatch):
    repo = MagicMock()
    dados = {
        "7": {"almoco": 1, "vegano": 1, "tradicional": 0, "silencioso": True},
        "8": {"almoco": 1, "pausado": True},
        "9": {"almoco": 1, "bloqueado": True},
        "10": {"almoco": 1, "dias": []},
    }
    repo.pegar_todos_usuarios.return_value = dados
    repo.pegar_usuario.side_effect = dados.get
    monkeypatch.setattr(service, "get_firebase", lambda: repo)
    registro = DeliveryRepository(Reference())
    monkeypatch.setattr("integrations.firebase.delivery_repository.DeliveryRepository", lambda: registro)
    sender = SimpleNamespace(enviar=AsyncMock(return_value=SimpleNamespace(erro=None, message_id=42)))
    context = SimpleNamespace(bot=object(), bot_data={"delivery_sender": sender})
    dia = datetime(2026, 9, 6, 12, tzinfo=FUSO)
    await service.entregar_telegram(context, ["Arroz"] * 5, [("Arroz", "Almoço Tradicional")], dia, "almoco")
    assert sender.enviar.await_count == 2
    assert sender.enviar.call_args.args[1] == "7"
    assert sender.enviar.call_args.args[-1] is True
    await service.entregar_telegram(context, ["Arroz"] * 5, [("Arroz", "Almoço Tradicional")], dia, "almoco")
    assert sender.enviar.await_count == 2


def test_nenhum_dia_persiste_como_zero():
    from modules.preferences.rules import dias_ativos

    repo = Config(Reference())
    repo.criar_usuario("7")
    for dia in range(7):
        repo.definir_dia("7", dia, False)
    assert repo.pegar_usuario("7")["dias"] == 0
    assert dias_ativos(repo.pegar_usuario("7")) == ()


def test_exclusao_remove_cadastro_e_entregas_atomicamente():
    ref = MagicMock()
    ref.key = "usuarios"
    repo = Config(ref)
    assert repo.excluir_usuario("7")
    ref.parent.update.assert_called_once_with({"usuarios/7": None, "entregas/7": None})
    ref.child.assert_not_called()


async def test_fragmentos_confirmados_nao_repetem_apos_falha(monkeypatch):
    repo = MagicMock()
    repo.pegar_todos_usuarios.return_value = {}
    monkeypatch.setattr(service, "get_firebase", lambda: repo)
    registro = DeliveryRepository(Reference())
    monkeypatch.setattr("integrations.firebase.delivery_repository.DeliveryRepository", lambda: registro)
    ok = SimpleNamespace(erro=None, message_id=42)
    sender = SimpleNamespace(enviar=AsyncMock(side_effect=[ok, SimpleNamespace(erro="limite", message_id=None), ok]))
    context = SimpleNamespace(bot=object(), bot_data={"delivery_sender": sender})
    dia = datetime(2026, 9, 6, 12, tzinfo=FUSO)
    itens = [("Arroz " * 800, "Almoço Tradicional")]
    assert not await service.entregar_telegram(context, [""] * 5, itens, dia, "almoco")
    assert await service.entregar_telegram(context, [""] * 5, itens, dia, "almoco")
    assert sender.enviar.await_count == 3
