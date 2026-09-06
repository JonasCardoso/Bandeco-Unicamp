"""Fluxos reais de navegação com fronteiras externas simuladas."""

import asyncio
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.error import BadRequest, Forbidden, RetryAfter, TimedOut

from interfaces.telegram import navigation as nav
from interfaces.telegram import screens
from interfaces.telegram.commands import general
from interfaces.telegram.commands.balance import cancelar, saldo
from modules.menu.view import adaptar


@pytest.fixture
def fluxo(monkeypatch):
    repo = MagicMock()
    repo.pegar_usuario.return_value = {"tradicional": 1, "vegano": 0, "cafe": 0, "almoco": 0, "jantar": 0}
    repo.criar_usuario.return_value = True
    repo.definir_preferencias.return_value = True
    monkeypatch.setattr(nav, "get_firebase", lambda: repo)
    monkeypatch.setattr(nav, "hoje", lambda: date(2026, 9, 6))
    monkeypatch.setattr(nav.rate_limiter_cardapio, "is_allowed", lambda _: True)
    bot = SimpleNamespace(
        send_message=AsyncMock(return_value=SimpleNamespace(message_id=11)),
        edit_message_text=AsyncMock(return_value=SimpleNamespace(message_id=11)),
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=7, type="private"),
        callback_query=None,
        message=SimpleNamespace(text="", message_id=8),
    )
    context = SimpleNamespace(bot=bot, user_data={}, bot_data={}, args=[], application=MagicMock())
    return update, context, repo


def clicar(update, dado):
    update.callback_query = SimpleNamespace(
        data=dado, answer=AsyncMock(), from_user=SimpleNamespace(id=7), message=SimpleNamespace(message_id=11)
    )


async def test_start_preserva_existente_e_abre_painel(fluxo):
    update, context, repo = fluxo
    await nav.iniciar(update, context)
    repo.definir_preferencias.assert_not_called()
    assert "O que você quer" in context.bot.send_message.call_args.kwargs["text"]


async def test_cadastro_novo_oferece_escolha(fluxo):
    update, context, repo = fluxo
    repo.pegar_usuario.return_value = {"cadastro_concluido": False}
    await nav.iniciar(update, context)
    assert "desligadas" in context.bot.send_message.call_args.kwargs["text"]
    clicar(update, "v1:onboard:vegano")
    await nav.callback(update, context)
    repo.definir_preferencias.assert_called_with(7, {"tradicional": 0, "vegano": 1}, True)
    clicar(update, "v1:skip")
    await nav.callback(update, context)
    repo.definir_preferencias.assert_called_with(
        7, {"cadastro_concluido": True, "cafe": 0, "almoco": 0, "jantar": 0}, True
    )


async def test_callbacks_repetidos_definem_valor_explicito(fluxo):
    update, context, repo = fluxo
    clicar(update, "v1:set:almoco:1")
    await nav.callback(update, context)
    await nav.callback(update, context)
    assert [c.args for c in repo.definir_preferencias.call_args_list] == [(7, {"almoco": 1})] * 2
    assert update.callback_query.answer.await_count == 2


@pytest.mark.parametrize(
    "dado",
    [
        "v2:home",
        "v1:set:senha:1",
        "v1:set:almoco:9",
        "v1:meal:x:2026-09-06:vegano",
        "v1:meal:almoco:ontem:vegano",
        "v1:home:extra",
        "x" * 65,
    ],
)
async def test_callback_invalido_nao_altera_dados(fluxo, dado):
    update, context, repo = fluxo
    clicar(update, dado)
    await nav.callback(update, context)
    repo.definir_preferencias.assert_not_called()
    assert "Reabra" in context.bot.edit_message_text.call_args.kwargs["text"]


async def test_callback_de_outro_usuario_ignorado(fluxo):
    update, context, repo = fluxo
    clicar(update, "v1:set:almoco:1")
    update.callback_query.from_user.id = 9
    await nav.callback(update, context)
    repo.definir_preferencias.assert_not_called()


async def test_exclusao_exige_confirmacao_e_expira(fluxo):
    update, context, repo = fluxo
    clicar(update, "v1:delete_confirm")
    await nav.callback(update, context)
    repo.excluir_usuario.assert_not_called()
    await nav.excluir(update, context)
    await nav.callback(update, context)
    repo.excluir_usuario.assert_called_once_with(7)
    assert context.user_data == {}


async def test_cardapio_com_data_e_nutricao_sem_mudar_preferencia(fluxo, monkeypatch):
    update, context, repo = fluxo
    monkeypatch.setattr(nav, "comida", lambda _: ["Frango", "Tofu <teste>", "Sopa", "Legumes", "Pão"])
    clicar(update, "v1:meal:almoco:2026-09-06:vegano")
    await nav.callback(update, context)
    ultima = context.bot.edit_message_text.call_args.kwargs
    assert "06/09/2026" in ultima["text"] and "Tofu <teste>" in ultima["text"]
    assert ultima["parse_mode"] is None
    callbacks = [b.callback_data for linha in ultima["reply_markup"].inline_keyboard for b in linha]
    assert "v1:nutrition:almoco:2026-09-06:vegano" in callbacks
    assert "v1:meal:almoco:2026-09-07:vegano" in callbacks
    repo.definir_preferencias.assert_not_called()


async def test_dias_na_virada_da_semana(fluxo):
    update, context, _ = fluxo
    clicar(update, "v1:dates:jantar:2026-09-06:tradicional")
    await nav.callback(update, context)
    botoes = context.bot.edit_message_text.call_args.kwargs["reply_markup"].inline_keyboard
    assert "Dom 06/09" == botoes[0][0].text
    assert "Seg 07/09" == botoes[1][0].text


@pytest.mark.parametrize(
    "dados,estado",
    [
        (None, "erro"),
        ([""] * 5, "pendente"),
        (["Refeição não cadastrada."] * 5, "ausente"),
        (["Arroz"] * 5, "disponivel"),
    ],
)
@pytest.mark.parametrize("refeicao", ["cafe", "almoco", "jantar"])
def test_estados_cardapio(dados, estado, refeicao):
    assert adaptar(dados, date(2026, 9, 6), refeicao, "vegano").estado == estado


async def test_edicao_inacessivel_reabre_tela(fluxo):
    update, context, _ = fluxo
    context.bot.edit_message_text.side_effect = BadRequest("Message to edit not found")
    resultado = await screens.enviar(context.bot, 7, "Painel", message_id=10)
    assert resultado.message_id == 11
    context.bot.send_message.assert_awaited_once()


async def test_edicao_identica_nao_duplica(fluxo):
    _, context, _ = fluxo
    context.bot.edit_message_text.side_effect = BadRequest("Message is not modified")
    resultado = await screens.enviar(context.bot, 7, "Painel", message_id=10)
    assert resultado.message_id == 10
    context.bot.send_message.assert_not_awaited()


@pytest.mark.parametrize(
    "erro,tipo", [(Forbidden("blocked"), "bloqueado"), (TimedOut(), "incerto"), (RetryAfter(1), "limite")]
)
async def test_envio_classifica_falhas(fluxo, erro, tipo):
    _, context, _ = fluxo
    context.bot.send_message.side_effect = erro
    assert (await screens.enviar(context.bot, 7, "Painel")).erro == tipo


async def test_saldo_somente_apos_comando_e_no_privado(fluxo, monkeypatch):
    update, context, _ = fluxo
    processar = AsyncMock()
    monkeypatch.setattr(general, "_processar_saldo", processar)
    update.message.text = "123456 senha"
    await general.mensagem(update, context)
    processar.assert_not_awaited()
    await saldo(update, context)
    await general.mensagem(update, context)
    processar.assert_awaited_once()
    await cancelar(update, context)
    assert "saldo_ate" not in context.user_data
    update.effective_chat.type = "group"
    await saldo(update, context)
    assert "saldo_ate" not in context.user_data


async def test_saldo_expirado_nao_consulta(fluxo, monkeypatch):
    update, context, _ = fluxo
    context.user_data["saldo_ate"] = 1
    update.message.text = "123456 senha"
    processar = AsyncMock()
    monkeypatch.setattr(general, "_processar_saldo", processar)
    await general.mensagem(update, context)
    processar.assert_not_awaited()
    assert "expirada" in context.bot.send_message.call_args.kwargs["text"]


async def test_bloqueio_preserva_preferencias(fluxo):
    update, context, repo = fluxo
    update.my_chat_member = SimpleNamespace(
        chat=update.effective_chat, new_chat_member=SimpleNamespace(status="kicked")
    )
    await nav.bloqueio(update, context)
    repo.definir_preferencias.assert_called_with(7, {"bloqueado": True})


async def test_nutricao_deduplica_trabalho():
    import threading

    from modules.nutrition.jobs import NutritionJobs

    jobs = NutritionJobs()
    entrada = threading.Event()
    liberar = threading.Event()

    def gerar(_):
        entrada.set()
        liberar.wait(timeout=2)
        return "imagem"

    gerador = MagicMock(side_effect=gerar)
    a = asyncio.create_task(jobs.gerar("arroz", gerador))
    await asyncio.to_thread(entrada.wait, 1)
    b = asyncio.create_task(jobs.gerar("arroz", gerador))
    await asyncio.sleep(0)
    liberar.set()
    assert await asyncio.gather(a, b) == ["imagem", "imagem"]
    gerador.assert_called_once()


async def test_registro_aponta_para_callback_correto(monkeypatch):
    from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

    from app.registry import configurar_comandos, register_handlers

    app = MagicMock()
    app.bot.set_my_commands = AsyncMock()
    register_handlers(app, CommandHandler, MessageHandler)
    handlers = [call.args[0] for call in app.add_handler.call_args_list]
    cb = next(h for h in handlers if isinstance(h, CallbackQueryHandler))
    assert cb.callback is nav.callback
    assert any(isinstance(h, CommandHandler) and "menu" in h.commands for h in handlers)
    await configurar_comandos(app)
    assert any(c.command == "menu" for c in app.bot.set_my_commands.call_args.args[0])


async def test_botao_nutricao_inicia_tarefa_sem_bloquear(fluxo, monkeypatch):
    from interfaces.telegram import nutrition_tasks

    update, context, _ = fluxo
    monkeypatch.setattr(nutrition_tasks, "comida", lambda _: ["Arroz"] * 5)
    processar = AsyncMock()
    monkeypatch.setattr(nutrition_tasks, "processar", processar)
    tarefas = []
    context.application.create_task.side_effect = lambda coro, **kw: tarefas.append(coro)
    clicar(update, "v1:nutrition:almoco:2026-09-06:vegano")
    await nav.callback(update, context)
    processar.assert_not_awaited()
    await nav.callback(update, context)
    assert len(tarefas) == 1
    await tarefas[0]
    processar.assert_awaited_once()
    assert "Arroz" in processar.call_args.args[2]
    assert not context.bot_data["nutrition_users"]


async def test_texto_longo_nao_perde_conteudo(fluxo):
    from shared.text import fragmentos

    _, context, _ = fluxo
    texto = "🍽️" * 3000
    partes = fragmentos(texto)
    assert "".join(partes) == texto
    assert all(len(p.encode("utf-16-le")) // 2 <= 4000 for p in partes)
    await screens.enviar(context.bot, 7, texto)
    assert context.bot.send_message.await_count == len(partes)


async def test_falha_menu_comandos_nao_aborta_startup():
    from app.registry import configurar_comandos

    app = SimpleNamespace(bot=SimpleNamespace(set_my_commands=AsyncMock(side_effect=TimedOut())))
    await configurar_comandos(app)
    app.bot.set_my_commands.assert_awaited_once()
