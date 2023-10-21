import requests as req
from telegram import Update
from telegram.ext import CallbackContext

from senha import criptografarSenha
from util import URL_SALDO


async def saldoBandeco(update: Update, context: CallbackContext, ra, senha, log):
    try:
        senhaMD5, senhaSHA256, senhaSHA512 = criptografarSenha(senha)
        URL = URL_SALDO

        data = {"rauser": ra,
                "rapassword": senhaMD5,
                "rapassword2": senhaSHA256,
                "rapassword3": senhaSHA512}

        response = req.post(URL, timeout=5, data=data)

        if response.json().get('erro') is not None:
            return 'Usuário e/ou Senha Inválido(s)'
        else:
            valor = "{:.2f}".format(response.json()['cartao'][0]['saldo']).replace('.', ',')
            return f"O saldo do RA {ra} é de R${valor}"

    except Exception as error:
        log.adicionarLog(f'saldoBandeco - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                         f'{update.effective_chat.username} - Não foi possível consultar o saldo do RA\n{error}')
        await log.enviarLog(context)
        return None
