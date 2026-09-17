"""Ajuda, contato e roteamento das mensagens livres."""

import asyncio
import datetime as dt
import time
from datetime import timedelta
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import CallbackContext

from core.constants import DIAS
from integrations.firebase.user_repository import get_firebase
from integrations.unicamp.menu_client import comida
from interfaces.telegram.commands.preferences import modalidade, notificacao
from interfaces.telegram.help_text import AJUDA, SECOES_AJUDA
from interfaces.telegram.keyboards import teclado_contato
from interfaces.telegram.logging import Log
from interfaces.telegram.messaging import deletar_mensagem, mandar_mensagem, mandar_mensagem_teclado
from interfaces.telegram.screens import enviar
from modules.balance.service import saldo_bandeco
from modules.balance.validation import validar_saldo_entrada
from modules.menu.service import modalidade_com_cardapio
from modules.notifications.service import mensagem_cardapio_telegram
from shared.rate_limit import rate_limiter_cardapio, rate_limiter_saldo


def _contexto_chat(update: Update) -> dict:
    chat = update.effective_chat
    return {"chat_id": chat.id, "username": chat.username, "full_name": chat.full_name}


async def _registrar_falha(log: Log, context: CallbackContext, update: Update, event: str, mensagem: str) -> None:
    log.error(mensagem, component="telegram.router", event=event, context=_contexto_chat(update))
    await log.enviar_log(context)


async def contato(update: Update, context: CallbackContext):
    if update.effective_chat.type != "private":
        return
    buttons = teclado_contato()
    await mandar_mensagem_teclado(
        context,
        update.effective_chat.id,
        "Compartilhe seu próprio telefone apenas se desejar mantê-lo no cadastro. Não há envio automático por WhatsApp. Remova com /reset_contato.",
        buttons,
    )


async def ajuda(update: Update, context: CallbackContext):
    await enviar(context.bot, update.effective_chat.id, AJUDA, destacar_titulo=True, secoes_negrito=SECOES_AJUDA)


async def mensagem_contato(update: Update, context: CallbackContext):
    if update.effective_chat.type != "private":
        return
    log = Log()
    repositorio = get_firebase()
    dados = await asyncio.to_thread(repositorio.pegar_usuario, update.effective_chat.id)
    contato_recebido = update.message.contact if update.message is not None else None
    if dados and contato_recebido and contato_recebido["user_id"] == update.effective_chat.id:
        dados["telefone"] = str(contato_recebido["phone_number"]).replace("+", "")
        atualizado = await asyncio.to_thread(repositorio.adicionar_contato, dados, update.effective_chat.id)
        if atualizado:
            await mandar_mensagem(context, update.effective_chat.id, "Contato atualizado !")
        else:
            await _registrar_falha(
                log, context, update, "contact_update_failed", "Não foi possível atualizar o contato"
            )
        return

    await _registrar_falha(log, context, update, "contact_user_missing", "Não foi possível obter o usuário")


async def _processar_cardapio(
    update: Update,
    context: CallbackContext,
    log: Log,
    hoje: dt.datetime,
    texto: str,
) -> None:
    if not rate_limiter_cardapio.is_allowed(str(update.effective_chat.id)):
        await mandar_mensagem(
            context,
            update.effective_chat.id,
            "⚠️ *Aguarde um momento!*\n\nVocê atingiu o limite de consultas. Tente novamente em breve.",
            parse_mode="Markdown",
        )
        return

    periodo, dia_nome = (parte.strip() for parte in texto.rsplit("de", 1))
    dia = hoje - timedelta(days=hoje.weekday() - DIAS.index(dia_nome))
    comida_resultado = await asyncio.to_thread(comida, dia.strftime("%Y-%m-%d"))
    if comida_resultado is None:
        await mandar_mensagem(context, update.effective_chat.id, "Algo deu errado !")
        await _registrar_falha(log, context, update, "menu_fetch_failed", "Não foi possível consultar o cardápio")
        return

    repositorio = get_firebase()
    dados = await asyncio.to_thread(repositorio.pegar_usuario, update.effective_chat.id)
    if not dados:
        await _registrar_falha(log, context, update, "menu_user_missing", "Não foi possível obter o usuário")
        return

    cardapio = modalidade_com_cardapio(comida_resultado, dados, periodo)
    await mensagem_cardapio_telegram(update.effective_chat.id, context, cardapio, dia)


async def _processar_preferencia(update: Update, context: CallbackContext, log: Log, texto: str) -> None:
    repositorio = get_firebase()
    dados = await asyncio.to_thread(repositorio.pegar_usuario, update.effective_chat.id)
    if not dados:
        await _registrar_falha(log, context, update, "preference_user_missing", "Não foi possível obter o usuário")
        return

    campos = {
        "Tradicional": "tradicional",
        "Vegano": "vegano",
        "Café": "cafe",
        "Almoço": "almoco",
        "Jantar": "jantar",
    }
    selecionado = next((campo for rotulo, campo in campos.items() if rotulo in texto), None)
    if selecionado is None:
        return
    dados[selecionado] = 0 if dados[selecionado] else 1

    atualizado = await asyncio.to_thread(
        repositorio.definir_preferencias, update.effective_chat.id, {selecionado: dados[selecionado]}
    )
    if not atualizado:
        await _registrar_falha(
            log,
            context,
            update,
            "preference_update_failed",
            "Não foi possível atualizar o usuário",
        )
        return

    if selecionado in {"tradicional", "vegano"}:
        await modalidade(update, context)
    else:
        await notificacao(update, context)


async def _processar_saldo(update: Update, context: CallbackContext, log: Log, texto: str) -> None:
    ra_numero, senha = texto.split()
    if not rate_limiter_saldo.is_allowed(str(update.effective_chat.id)):
        await mandar_mensagem(
            context,
            update.effective_chat.id,
            "⚠️ *Aguarde um momento!*\n\nVocê atingiu o limite de consultas. Tente novamente em breve.",
            parse_mode="Markdown",
        )
        return

    if not validar_saldo_entrada(ra_numero, senha):
        await mandar_mensagem(
            context,
            update.effective_chat.id,
            "⚠️ *Formato inválido!*\n\n"
            "Use: `<ra> <senha>`\n\n"
            "Exemplo: `123456 abc123`\n\n"
            "(onde RA é numérico e senha não deve conter espaços)",
            parse_mode="Markdown",
        )
        return

    await deletar_mensagem(context, update.effective_chat.id, update.message.message_id)
    context.user_data.pop("saldo_ate", None)
    valor = await saldo_bandeco(update, context, ra_numero, senha, log)
    if valor is not None:
        await mandar_mensagem(context, update.effective_chat.id, valor)


async def mensagem(update: Update, context: CallbackContext):
    """Direciona mensagens livres para um único fluxo de negócio."""
    if update.message is None or update.message.text is None:
        return

    texto = update.message.text
    log = Log()
    partes_dia = texto.rsplit("de", 1)
    if len(partes_dia) == 2 and partes_dia[1].strip() in DIAS:
        await _processar_cardapio(update, context, log, dt.datetime.now(ZoneInfo("America/Sao_Paulo")), texto)
    elif "Ativo" in texto or "Inativo" in texto:
        await _processar_preferencia(update, context, log, texto)
    elif update.effective_chat.type == "private" and context.user_data.get("saldo_ate", 0) > time.monotonic():
        if len(texto.split()) != 2:
            await mandar_mensagem(
                context, update.effective_chat.id, "Informe RA e senha ou use /cancelar.", parse_mode=None
            )
            return
        await _processar_saldo(update, context, log, texto)
    elif context.user_data.pop("saldo_ate", None) is not None:
        await mandar_mensagem(
            context, update.effective_chat.id, "Consulta expirada. Use /saldo novamente.", parse_mode=None
        )
