"""Consulta de saldo do cartão Bandeco.

Este módulo fornece funções para consultar o saldo do cartão universitário
dos alunos através da API do Bandeco.
"""

import asyncio
from typing import Optional

import requests as requests  # noqa: F401 - ponto de patch compatível para testes/consumidores
from telegram import Update
from telegram.ext import CallbackContext

from core.config import get_url_saldo
from integrations.unicamp.balance_client import _post_saldo

from .crypto import criptografar_senha


async def saldo_bandeco(update: Update, context: CallbackContext, ra_numero: str, senha: str, log) -> Optional[str]:
    """Consulta o saldo do cartão Bandeco para um RA e senha.

    Args:
        update: Objeto Update do Telegram.
        context: Contexto do bot Telegram.
        ra_numero: Número do RA do aluno.
        senha: Senha do RA.
        log: Instância de Log para registro de erros.

    Returns:
        String com o saldo formatado ou None em caso de erro.
    """
    try:
        hash_md5, hash_SHA256, hash_SHA512 = criptografar_senha(senha)
        url = get_url_saldo()

        data = {
            "rauser": ra_numero,
            "rapassword": hash_md5,
            "rapassword2": hash_SHA256,
            "rapassword3": hash_SHA512,
        }

        response = await asyncio.to_thread(_post_saldo, url, data)

        if response.json().get("erro") is not None:
            return "Usuário e/ou Senha Inválido(s)"
        else:
            valor = "{:.2f}".format(response.json()["cartao"][0]["saldo"]).replace(".", ",")
            return f"O saldo do RA {ra_numero} é de R$ {valor}"

    except Exception as error:
        log.error(
            f"Não foi possível consultar o saldo: {type(error).__name__}",
            component="balance",
            event="query_failed",
            context={"chat_id": update.effective_chat.id, "username": update.effective_chat.username},
        )
        await log.enviar_log(context)
        return None
