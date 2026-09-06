"""Painel privado e callbacks versionados; textos de botões não são comandos."""

import asyncio
import logging
import time
from datetime import date, timedelta

from telegram import InlineKeyboardButton as Button
from telegram import InlineKeyboardMarkup
from telegram.error import TelegramError

from integrations.firebase.user_repository import get_firebase
from integrations.unicamp.menu_client import comida
from integrations.unicamp.price_client import obter_valores_refeicao
from integrations.unicamp.schedule_client import horario_funcionamento
from interfaces.telegram.commands.balance import saldo
from interfaces.telegram.commands.cameras import ra, rs, ru
from interfaces.telegram.help_text import AJUDA, SECOES_AJUDA
from interfaces.telegram.rich_messages import cardapio_html, tentar
from interfaces.telegram.screens import enviar
from modules.menu.view import REFEICOES, adaptar, hoje
from modules.preferences.rules import dias_ativos
from shared.keyed_lock import user_lock
from shared.rate_limit import rate_limiter_cardapio

logger = logging.getLogger(__name__)
CAMPOS = {"tradicional", "vegano", "cafe", "almoco", "jantar", "pausado", "silencioso"}
DIAS = ("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")


def botao(texto, *partes):
    dado = ":".join(("v1", *map(str, partes)))
    if len(dado.encode()) > 64:
        raise ValueError("Callback excede 64 bytes")
    return Button(texto, callback_data=dado)


def teclado(linhas, voltar="home"):
    return InlineKeyboardMarkup([*linhas, [botao("Voltar", voltar), botao("Início", "home")]])


async def tela(update, context, texto, markup, message_id=None, destacar_titulo=False, secoes_negrito=()):
    query = update.callback_query
    if message_id is None and query and query.message:
        message_id = query.message.message_id
    resultado = await enviar(
        context.bot,
        update.effective_chat.id,
        texto,
        markup,
        message_id,
        destacar_titulo=destacar_titulo,
        secoes_negrito=secoes_negrito,
    )
    return resultado.message_id


async def menu(update, context):
    context.user_data.pop("saldo_ate", None)
    if update.effective_chat.type != "private":
        await enviar(context.bot, update.effective_chat.id, "Abra o bot no privado para usar /menu.")
        return
    dados = await asyncio.to_thread(get_firebase().pegar_usuario, update.effective_chat.id)
    tipo = "vegano" if dados and dados.get("vegano") and not dados.get("tradicional") else "tradicional"
    await tela(
        update,
        context,
        "Bandeco Unicamp\nO que você quer consultar?",
        InlineKeyboardMarkup(
            [
                [botao("Cardápio de hoje", "meal", "almoco", hoje().isoformat(), tipo)],
                [
                    botao("Café da manhã", "meal", "cafe", hoje().isoformat(), tipo),
                    botao("Jantar", "meal", "jantar", hoje().isoformat(), tipo),
                ],
                [botao("Câmeras", "cams"), botao("Horários e preços", "info")],
                [botao("Saldo", "saldo"), botao("Preferências", "prefs")],
                [botao("Ajuda", "help")],
            ]
        ),
        destacar_titulo=True,
    )


async def iniciar(update, context):
    if update.effective_chat.type != "private":
        await menu(update, context)
        return
    repo = get_firebase()
    if not await asyncio.to_thread(repo.criar_usuario, update.effective_chat.id):
        await enviar(
            context.bot, update.effective_chat.id, "Não foi possível abrir seu cadastro. Tente /start novamente."
        )
        return
    dados = await asyncio.to_thread(repo.pegar_usuario, update.effective_chat.id)
    if not dados:
        await enviar(context.bot, update.effective_chat.id, "Cadastro indisponível. Tente /start novamente.")
        return
    args = context.args or []
    if args:
        partes = args[0].split("_")
        if partes == ["preferencias"]:
            await preferencias(update, context)
            return
        if len(partes) == 4 and partes[0] == "cardapio":
            try:
                refeicao, dia, modalidade = validar_cardapio(partes[1:])
            except ValueError:
                pass
            else:
                await cardapio(update, context, refeicao, dia, modalidade)
                return
    if dados.get("cadastro_concluido", True) is False:
        await tela(
            update,
            context,
            "Bem-vindo! Qual modalidade você prefere? As notificações começam desligadas.",
            teclado(
                [
                    [botao("Tradicional", "onboard", "tradicional"), botao("Vegano", "onboard", "vegano")],
                    [botao("Ambos", "onboard", "ambos"), botao("Agora não", "skip")],
                ]
            ),
        )
    else:
        await menu(update, context)


async def preferencias(update, context):
    if update.effective_chat.type != "private":
        return
    dados = await asyncio.to_thread(get_firebase().pegar_usuario, update.effective_chat.id)
    if not dados:
        await tela(update, context, "Use /start para criar ou recuperar seu cadastro.", teclado([]))
        return
    linhas = []
    for campo, nome in [
        ("tradicional", "Tradicional"),
        ("vegano", "Vegano"),
        ("cafe", "Café"),
        ("almoco", "Almoço"),
        ("jantar", "Jantar"),
        ("pausado", "Pausar notificações"),
        ("silencioso", "Envio silencioso"),
    ]:
        ativo = bool(dados.get(campo, False))
        linhas.append([botao(f"{'✓' if ativo else '○'} {nome}", "set", campo, int(not ativo))])
    dias = dias_ativos(dados)
    linhas.append(
        [botao(f"{'✓' if i in dias else '○'} {nome}", "day", i, int(i not in dias)) for i, nome in enumerate(DIAS)]
    )
    linhas.extend([[botao("Concluir", "done")], [botao("Excluir cadastro", "delete")]])
    await tela(
        update,
        context,
        "Preferências\nSelecione refeições e dias para receber notificações.\n"
        "A pausa preserva suas escolhas. Horários seguem a programação do bot.\n"
        "Sem modalidade marcada, serão exibidas ambas.",
        teclado(linhas),
        destacar_titulo=True,
    )


def validar_cardapio(partes):
    if len(partes) != 3:
        raise ValueError("Formato inválido")
    refeicao, data, modalidade = partes
    dia = date.fromisoformat(data)
    if refeicao not in REFEICOES or modalidade not in {"tradicional", "vegano"}:
        raise ValueError("Opção inválida")
    if abs((dia - hoje()).days) > 366:
        raise ValueError("Data fora do intervalo")
    return refeicao, dia, modalidade


async def cardapio(update, context, refeicao, dia, modalidade):
    linhas = [
        [
            botao("Hoje", "meal", refeicao, hoje(), modalidade),
            botao("Amanhã", "meal", refeicao, hoje() + timedelta(days=1), modalidade),
            botao("Escolher dia", "dates", refeicao, dia, modalidade),
        ]
    ]
    if refeicao != "cafe":
        linhas.append(
            [
                botao("Tradicional", "meal", refeicao, dia, "tradicional"),
                botao("Vegano", "meal", refeicao, dia, "vegano"),
            ]
        )
    if not rate_limiter_cardapio.is_allowed(str(update.effective_chat.id)):
        await tela(update, context, "Aguarde um momento antes de consultar novamente.", teclado(linhas))
        return
    mid = await tela(update, context, "Consultando cardápio…", teclado(linhas))
    inicio = time.monotonic()
    dados = await asyncio.to_thread(comida, dia.isoformat())
    item = adaptar(dados, dia, refeicao, modalidade)
    logger.info("menu_consulta estado=%s duracao=%.3f", item.estado, time.monotonic() - inicio)
    if item.estado == "disponivel":
        linhas.append([botao("Ver nutrição", "nutrition", refeicao, dia, modalidade)])
    else:
        linhas.append([botao("Tentar novamente", "meal", refeicao, dia, modalidade)])
    if not await tentar(context.bot, update.effective_chat.id, cardapio_html(item), teclado(linhas), mid):
        await tela(update, context, item.texto, teclado(linhas), mid, destacar_titulo=True)


async def excluir(update, context):
    if update.effective_chat.type != "private":
        return
    context.user_data["excluir_ate"] = time.monotonic() + 300
    await tela(
        update,
        context,
        "Excluir cadastro, preferências e telefone? Esta ação não pode ser desfeita.",
        teclado([[botao("Confirmar exclusão", "delete_confirm"), botao("Cancelar", "home")]]),
    )


async def bloqueio(update, context):
    evento = update.my_chat_member
    if evento and evento.chat.type == "private":
        repo = get_firebase()
        if await asyncio.to_thread(repo.pegar_usuario, evento.chat.id):
            await asyncio.to_thread(
                repo.definir_preferencias, evento.chat.id, {"bloqueado": evento.new_chat_member.status == "kicked"}
            )


async def callback(update, context):
    query = update.callback_query
    if not query:
        return
    try:
        await query.answer()
    except TelegramError:
        pass
    if not update.effective_chat or update.effective_chat.type != "private":
        return
    if query.from_user.id != update.effective_chat.id:
        return
    try:
        if not isinstance(query.data, str):
            raise ValueError("Callback inválido")
        partes = query.data.split(":")
        if len((query.data or "").encode()) > 64 or partes[0] != "v1" or len(partes) < 2:
            raise ValueError("Versão inválida")
        acao, args = partes[1], partes[2:]
        if acao != "saldo":
            context.user_data.pop("saldo_ate", None)
        if acao in {"meal", "dates", "nutrition"}:
            refeicao, dia, modalidade = validar_cardapio(args)
            if acao == "meal":
                await cardapio(update, context, refeicao, dia, modalidade)
            elif acao == "dates":
                await tela(
                    update,
                    context,
                    "Escolha a data",
                    teclado(
                        [
                            [botao(f"{DIAS[d.weekday()]} {d:%d/%m}", "meal", refeicao, d, modalidade)]
                            for d in [hoje() + timedelta(days=i) for i in range(7)]
                        ]
                    ),
                )
            else:
                from interfaces.telegram.nutrition_tasks import solicitar

                await solicitar(update, context, refeicao, dia, modalidade)
            return
        if acao == "set" and len(args) == 2 and args[0] in CAMPOS and args[1] in {"0", "1"}:
            if not await asyncio.to_thread(
                get_firebase().definir_preferencias, update.effective_chat.id, {args[0]: int(args[1])}
            ):
                raise RuntimeError("Persistência indisponível")
            await preferencias(update, context)
            return
        if acao == "day" and len(args) == 2 and args[0] in set(map(str, range(7))) and args[1] in {"0", "1"}:
            if not await asyncio.to_thread(
                get_firebase().definir_dia, update.effective_chat.id, int(args[0]), args[1] == "1"
            ):
                raise RuntimeError("Persistência indisponível")
            await preferencias(update, context)
            return
        if acao == "onboard" and args in [["tradicional"], ["vegano"], ["ambos"]]:
            dados = {"tradicional": int(args[0] != "vegano"), "vegano": int(args[0] != "tradicional")}
            if not await asyncio.to_thread(get_firebase().definir_preferencias, update.effective_chat.id, dados, True):
                raise RuntimeError("Persistência indisponível")
            await preferencias(update, context)
            return
        if acao == "cam" and args in [["ru"], ["ra"], ["rs"]]:
            await tela(update, context, "Consultando câmera…", teclado([], "cams"))
            enviadas = await {"ru": ru, "ra": ra, "rs": rs}[args[0]](update, context)
            await tela(
                update,
                context,
                (
                    "Imagens consultadas. A fonte não informa o horário de captura; imagens podem estar em cache."
                    if enviadas
                    else "Uma ou mais imagens estão indisponíveis. Tente atualizar em um minuto."
                ),
                teclado([[botao("Atualizar", "cam", args[0])]], "cams"),
            )
            return
        if args:
            raise ValueError("Parâmetros inválidos")
        if acao == "home":
            context.user_data.pop("excluir_ate", None)
            await menu(update, context)
        elif acao == "prefs":
            await preferencias(update, context)
        elif acao in {"done", "skip"}:
            dados = {"cadastro_concluido": True}
            if acao == "skip":
                dados.update(cafe=0, almoco=0, jantar=0)
            if not await asyncio.to_thread(get_firebase().definir_preferencias, update.effective_chat.id, dados, True):
                raise RuntimeError("Persistência indisponível")
            await menu(update, context)
        elif acao == "saldo":
            await saldo(update, context)
        elif acao == "cams":
            await tela(
                update,
                context,
                "Câmeras dos restaurantes\n\nEscolha o restaurante.",
                teclado([[botao(x.upper(), "cam", x) for x in ("ru", "ra", "rs")]]),
                destacar_titulo=True,
            )
        elif acao == "info":
            await tela(
                update,
                context,
                "Horários e preços",
                teclado([[botao("Horários", "hours"), botao("Preços", "prices")]]),
                destacar_titulo=True,
            )
        elif acao in {"hours", "prices"}:
            mid = await tela(update, context, "Consultando…", teclado([], "info"))
            resultado = await asyncio.to_thread(horario_funcionamento if acao == "hours" else obter_valores_refeicao)
            from bs4 import BeautifulSoup

            texto = (
                BeautifulSoup(resultado, "html.parser").get_text()
                if resultado
                else "Fonte indisponível. Tente novamente."
            )
            if resultado and acao == "hours":
                texto = "Horários de funcionamento\n\n" + texto
            await tela(
                update,
                context,
                texto,
                teclado([[botao("Atualizar", acao)]], "info"),
                mid,
                destacar_titulo=bool(resultado),
                secoes_negrito=("Café da Manhã", "Almoço e Jantar"),
            )
        elif acao == "help":
            await tela(update, context, AJUDA, teclado([]), destacar_titulo=True, secoes_negrito=SECOES_AJUDA)
        elif acao == "delete":
            await excluir(update, context)
        elif acao == "delete_confirm":
            if context.user_data.pop("excluir_ate", 0) < time.monotonic():
                raise ValueError("Confirmação expirada")
            async with user_lock(context.bot_data, update.effective_chat.id):
                if not await asyncio.to_thread(get_firebase().excluir_usuario, update.effective_chat.id):
                    raise RuntimeError("Persistência indisponível")
            context.user_data.clear()
            await tela(update, context, "Cadastro excluído. Para voltar, use /start.", None)
        else:
            raise ValueError("Ação desconhecida")
    except (ValueError, RuntimeError):
        await tela(
            update, context, "Esta ação expirou ou não pôde ser concluída. Reabra o painel com /menu.", teclado([])
        )
