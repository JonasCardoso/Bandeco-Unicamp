"""Consulta de saldo do cartão Bandeco.

Este módulo fornece funções para consultar o saldo do cartão universitário
dos alunos através da API do Bandeco.
"""

from typing import Optional

import requests
from telegram import Update
from telegram.ext import CallbackContext

from senha import criptografar_senha
from util import get_url_saldo, retry


@retry(max_attempts=3, delay=1.0, exceptions=requests.RequestException)
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

        response = requests.post(url, timeout=5, data=data)

        if response.json().get("erro") is not None:
            return "Usuário e/ou Senha Inválido(s)"
        else:
            valor = "{:.2f}".format(response.json()["cartao"][0]["saldo"]).replace(".", ",")
            return f"O saldo do RA {ra_numero} é de R$ {valor}"

    except Exception as error:
        log.adicionar_log(
            f"saldoBandeco - {update.effective_chat.id} - {update.effective_chat.full_name} - "
            f"{update.effective_chat.username} - Não foi possível consultar o saldo do RA\n{error}"
        )
        await log.enviar_log(context)
        return None
