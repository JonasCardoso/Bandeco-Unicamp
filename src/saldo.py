import requests as req
from telegram import Update
from telegram.ext import CallbackContext

from senha import criptografar_senha
from util import URL_SALDO


async def saldo_bandeco(update: Update, context: CallbackContext, ra_numero, senha, log):
    try:
        senha_MD5, senha_SHA256, senha_SHA512 = criptografar_senha(senha)
        url = URL_SALDO

        data = {"rauser": ra_numero,
                "rapassword": senha_MD5,
                "rapassword2": senha_SHA256,
                "rapassword3": senha_SHA512}

        response = req.post(url, timeout=5, data=data)

        if response.json().get('erro') is not None:
            return 'Usuário e/ou Senha Inválido(s)'
        else:
            valor = "{:.2f}".format(response.json()['cartao'][0]['saldo']).replace('.', ',')
            return f"O saldo do RA {ra_numero} é de R${valor}"

    except Exception as error:
        log.adicionar_log(f'saldoBandeco - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                          f'{update.effective_chat.username} - Não foi possível consultar o saldo do RA\n{error}')
        await log.enviar_log(context)
        return None
