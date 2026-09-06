"""Solicitações nutricionais acompanhadas pelo ciclo de vida do bot."""

import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from integrations.unicamp.menu_client import comida
from interfaces.telegram.messaging import mandar_imagem
from interfaces.telegram.rich_messages import habilitado, tabela_html, tentar
from interfaces.telegram.screens import enviar
from modules.menu.view import adaptar
from modules.nutrition.jobs import NutritionJobs
from modules.nutrition.pipeline import dados_tabela_nutricional, gerar_tabela_nutricional

logger = logging.getLogger(__name__)


async def processar(context, chat_id, texto, message_id, gerador=gerar_tabela_nutricional, reply_id=None):
    jobs = context.bot_data.setdefault("nutrition_jobs", NutritionJobs())
    try:
        imagem = await jobs.gerar(texto, gerador)
        if imagem:
            if habilitado(chat_id):
                linhas = await asyncio.to_thread(dados_tabela_nutricional, texto)
                if linhas:
                    await tentar(context.bot, chat_id, tabela_html(linhas))
            enviado = await mandar_imagem(context, chat_id, imagem, reply_id)
            status = (
                "Tabela nutricional estimada, não oficial." if enviado else "Falha ao enviar imagem. Tente novamente."
            )
        else:
            status = "Não foi possível gerar a tabela agora. Tente novamente mais tarde."
    except Exception:
        logger.exception("nutrition_job_failed")
        status = "Não foi possível gerar a tabela. Tente novamente mais tarde."
    await enviar(
        context.bot,
        chat_id,
        status,
        InlineKeyboardMarkup([[InlineKeyboardButton("Início", callback_data="v1:home")]]),
        message_id,
    )


async def solicitar(update, context, refeicao, dia, modalidade):
    chat_id = update.effective_chat.id
    # Um pedido ativo por usuário também limita consultas repetidas à fonte.
    tarefas = context.bot_data.setdefault("nutrition_users", set())
    if chat_id in tarefas:
        return
    tarefas.add(chat_id)
    try:
        status = await enviar(context.bot, chat_id, "Preparando tabela nutricional…")
    except BaseException:
        tarefas.discard(chat_id)
        raise
    if status.erro:
        tarefas.discard(chat_id)
        return

    async def trabalho():
        try:
            dados = await asyncio.to_thread(comida, dia.isoformat())
            item = adaptar(dados, dia, refeicao, modalidade)
            if item.estado != "disponivel":
                await enviar(context.bot, chat_id, item.texto, message_id=status.message_id)
                return
            await processar(context, chat_id, item.texto, status.message_id)
        except Exception:
            logger.exception("nutrition_source_failed")
            await enviar(
                context.bot,
                chat_id,
                "Não foi possível consultar o cardápio. Tente novamente mais tarde.",
                message_id=status.message_id,
            )
        finally:
            tarefas.discard(chat_id)

    corrotina = trabalho()
    try:
        context.application.create_task(corrotina, update=update)
    except BaseException:
        corrotina.close()
        tarefas.discard(chat_id)
        raise
