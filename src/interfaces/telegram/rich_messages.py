"""Piloto Bot API 10.3: HTML estruturado isolado, opt-in e fallback convencional."""

import logging
from html import escape

from telegram.error import BadRequest, TelegramError

from core.settings import get_settings

logger = logging.getLogger(__name__)


def habilitado(chat_id):
    config = get_settings()
    return config.telegram_rich_enabled and str(chat_id) in config.telegram_rich_chat_ids.split(",")


def cardapio_html(item):
    titulo, _, texto = item.texto.partition("\n\n")
    conteudo = "".join(f"<p>{escape(linha)}</p>" for linha in texto.splitlines() if linha)
    botao = '<tg-button type="disabled">Nutrição indisponível</tg-button>' if item.estado != "disponivel" else ""
    return f"<h2>{escape(titulo)}</h2>{conteudo}{botao}"


def tabela_html(linhas):
    tabela = ""
    for indice, linha in enumerate(linhas):
        tag = "th" if indice == 0 else "td"
        tabela += "<tr>" + "".join(f"<{tag}>{escape(str(c))}</{tag}>" for c in linha) + "</tr>"
    return (
        "<h2>Nutrição estimada</h2><details><summary>Ver tabela e porções</summary>"
        f"<table bordered compact>{tabela}</table></details><footer>Estimativa não oficial.</footer>"
    )


async def tentar(bot, chat_id, html, markup=None, message_id=None):
    if not habilitado(chat_id):
        return False
    parametros = {"chat_id": chat_id, "rich_message": {"html": html}}
    if markup:
        parametros["reply_markup"] = markup.to_dict()
    if message_id:
        parametros["message_id"] = message_id
    try:
        await bot.do_api_request("editMessageText" if message_id else "sendRichMessage", api_kwargs=parametros)
        return True
    except BadRequest as erro:
        if "message is not modified" in str(erro).lower():
            return True
        logger.info("rich_message_fallback")
    except TelegramError:
        logger.info("rich_message_unavailable")
    return False
