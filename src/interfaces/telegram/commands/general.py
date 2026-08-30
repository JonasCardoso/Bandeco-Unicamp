"""Ajuda, contato e roteamento das mensagens livres."""

import datetime as dt
from datetime import timedelta

from telegram import Update
from telegram.ext import CallbackContext

from core.constants import DIAS
from integrations.firebase.user_repository import get_firebase
from integrations.unicamp.menu_client import comida
from interfaces.telegram.commands.preferences import modalidade, notificacao
from interfaces.telegram.keyboards import teclado_contato
from interfaces.telegram.logging import Log
from interfaces.telegram.messaging import (
    deletar_mensagem,
    mandar_mensagem,
    mandar_mensagem_teclado,
)
from modules.balance.service import saldo_bandeco
from modules.balance.validation import validar_saldo_entrada
from modules.menu.service import modalidade_com_cardapio
from modules.notifications.service import mensagem_cardapio_telegram
from shared.rate_limit import rate_limiter_cardapio, rate_limiter_saldo


async def contato(update: Update, context: CallbackContext):
    buttons = teclado_contato()
    await mandar_mensagem_teclado(
        context, update.effective_chat.id, "Compartilhe seu contato para ser notificado no WhatsApp", buttons
    )


async def ajuda(update: Update, context: CallbackContext):
    texto = r"""Com Bandeco Unicamp você pode consultar com facilidade os cardápios do RU, RS e RA da Unicamp.

Além de receber notificações diárias das suas modalidades cadastradas.

Use o /cafe para consultar o cardápio do café da manhã.
Use o /almoco para consultar o cardápio do almoço.
Use o /jantar para consultar o cardápio do jantar.

Use o /modalidade para definir entre a modalidade de cardápio vegano e/ou tradicional.
Use o /notificacao para escolher quais cardápios serão notificados.
Use o /horario para saber o horário de funcionamento dos restaurantes.
Use o /saldo para consultar o saldo no cartão universitário.
Use o /tabela para consultar a tabela nutricional não oficial do cardápio.
Use o /preco para consultar os valores atuais das refeições.

Use o /ru para receber imagens das câmeras do RU.
Use o /ra para receber imagens das câmeras do RA.
Use o /rs para receber imagens das câmeras do RS.

Use o /twitter para receber o link da página do Twitter.
Use o /instagram para receber o link da página do Instagram.
Use o /facebook para receber o link da página do Facebook.

Use o /desativar para apagar TODOS os seus dados cadastrados no bot.
Use o /reset\_modalidade para apagar suas preferências de modalidade (tradicional/vegano).
Use o /reset\_notificacao para desativar apenas as notificações diárias.

By @JonasCardoso"""
    await mandar_mensagem(context, update.effective_chat.id, texto)


async def mensagem_contato(update: Update, context: CallbackContext):
    log = Log()
    dados = get_firebase().pegar_usuario(update.effective_chat.id)
    if dados:
        if update.message.contact["user_id"] == update.effective_chat.id:
            dados["telefone"] = str(update.message.contact["phone_number"]).replace("+", "")
            if get_firebase().adicionar_contato(dados, update.effective_chat.id):
                await mandar_mensagem(context, update.effective_chat.id, "Contato atualizado !")
            else:
                log.adicionar_log(
                    f"mensagemContato - {update.effective_chat.id} - {update.effective_chat.full_name} -"
                    f"{update.effective_chat.username} - Não foi possível atualizar o contato"
                )
                await log.enviar_log(context)
            return

    log.adicionar_log(
        f"mensagemContato - {update.effective_chat.id} - {update.effective_chat.full_name} - "
        f"{update.effective_chat.username} - Não foi possível pegar o usuário"
    )
    await log.enviar_log(context)


async def mensagem(update: Update, context: CallbackContext):
    log = Log()
    # MessageHandler também pode receber uma mensagem editada por meio de
    # effective_message. Nesse caso, update.message é None e o update
    # não deve repetir consultas, alterações de preferência ou saldo.
    if update.message is None or update.message.text is None:
        return

    hoje = dt.datetime.today()

    if len(update.message.text.rsplit("de", 1)) == 2 and (update.message.text.rsplit("de", 1)[1].strip() in DIAS):
        # Rate limiting para consultas de cardápio
        if not rate_limiter_cardapio.is_allowed(str(update.effective_chat.id)):
            await mandar_mensagem(
                context,
                update.effective_chat.id,
                "⚠️ *Aguarde um momento!*\n\nVocê atingiu o limite de consultas. Tente novamente em breve.",
                parse_mode="Markdown",
            )
            return

        dia = hoje - timedelta(days=hoje.weekday() - DIAS.index(update.message.text.rsplit("de", 1)[1].strip()))
        data = dia.strftime("%Y-%m-%d")
        comida_resultado = comida(data)

        if comida_resultado is None:
            await mandar_mensagem(context, update.effective_chat.id, "Algo deu errado !")
            log.adicionar_log(
                f"{update.message.text} - {update.effective_chat.id} - {update.effective_chat.full_name} "
                f"- {update.effective_chat.username} - Não foi possível consultar o cardápio"
            )
            await log.enviar_log(context)

        else:
            dados = get_firebase().pegar_usuario(update.effective_chat.id)
            if not dados:
                log.adicionar_log(
                    f"mensagem - {update.effective_chat.id} - {update.effective_chat.full_name} - "
                    f"{update.effective_chat.username} - Não foi possível pegar o usuário"
                )
                await log.enviar_log(context)
                return

            periodo = update.message.text.rsplit("de", 1)[0].strip()
            cardapio = modalidade_com_cardapio(comida_resultado, dados, periodo)
            await mensagem_cardapio_telegram(update.effective_chat.id, context, cardapio, dia)

    elif "Ativo" in update.message.text or "Inativo" in update.message.text:
        dados = get_firebase().pegar_usuario(update.effective_chat.id)
        if not dados:
            log.adicionar_log(
                f"mensagem - {update.effective_chat.id} - {update.effective_chat.full_name} - "
                f"{update.effective_chat.username} - Não foi possível pegar o usuário"
            )
            await log.enviar_log(context)
            return

        if "Tradicional" in update.message.text:
            dados["tradicional"] = 0 if dados["tradicional"] else 1
        elif "Vegano" in update.message.text:
            dados["vegano"] = 0 if dados["vegano"] else 1
        elif "Café" in update.message.text:
            dados["cafe"] = 0 if dados["cafe"] else 1
        elif "Almoço" in update.message.text:
            dados["almoco"] = 0 if dados["almoco"] else 1
        elif "Jantar" in update.message.text:
            dados["jantar"] = 0 if dados["jantar"] else 1

        if not get_firebase().atualizar_usuario(dados, update.effective_chat.id):
            log.adicionar_log(
                f"mensagem - {update.effective_chat.id} - {update.effective_chat.full_name} - "
                f"{update.effective_chat.username} - Não foi possível atualizar o usuário"
            )
            await log.enviar_log(context)
            return

        if "Tradicional" in update.message.text or "Vegano" in update.message.text:
            await modalidade(update, context)
        else:
            await notificacao(update, context)

    elif len(update.message.text.split()) == 2 and update.message.text.split()[0].isnumeric():
        ra_numero = update.message.text.split()[0]
        senha = update.message.text.split()[1]

        # Rate limiting para consultas de saldo
        if not rate_limiter_saldo.is_allowed(str(update.effective_chat.id)):
            await mandar_mensagem(
                context,
                update.effective_chat.id,
                "⚠️ *Aguarde um momento!*\n\nVocê atingiu o limite de consultas. Tente novamente em breve.",
                parse_mode="Markdown",
            )
            return

        # Validação de entrada para RA e senha
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

        valor = await saldo_bandeco(update, context, ra_numero, senha, log)
        if valor is not None:
            await mandar_mensagem(context, update.effective_chat.id, valor)
