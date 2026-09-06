"""Envio e edição de telas com resultado estruturado, sem alterar helpers legados."""

import logging
from dataclasses import dataclass

from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TelegramError, TimedOut

from interfaces.telegram.formatting import titulo_em_negrito
from shared.text import fragmentos

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResultadoEnvio:
    message_id: int | None = None
    erro: str | None = None


async def enviar(
    bot, chat_id, texto, markup=None, message_id=None, silencioso=False, destacar_titulo=False, secoes_negrito=()
) -> ResultadoEnvio:
    partes = fragmentos(texto)
    if len(partes) > 1:
        for indice, parte in enumerate(partes):
            resultado = await enviar(
                bot,
                chat_id,
                parte,
                markup if indice == len(partes) - 1 else None,
                message_id if indice == 0 else None,
                silencioso,
                destacar_titulo and indice == 0,
                secoes_negrito,
            )
            if resultado.erro:
                return resultado
        return resultado
    entidades = (
        {"entities": titulo_em_negrito(texto, secoes_negrito, destacar_titulo)}
        if destacar_titulo or secoes_negrito
        else {}
    )
    try:
        if message_id:
            try:
                mensagem = await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=texto,
                    reply_markup=markup,
                    parse_mode=None,
                    **entidades,
                )
                return ResultadoEnvio(getattr(mensagem, "message_id", message_id))
            except BadRequest as erro:
                if "message is not modified" in str(erro).lower():
                    return ResultadoEnvio(message_id)
                # Mensagem removida/inacessível: uma nova tela permite continuar.
        mensagem = await bot.send_message(
            chat_id=chat_id,
            text=texto,
            reply_markup=markup,
            parse_mode=None,
            disable_notification=silencioso,
            **entidades,
        )
        return ResultadoEnvio(mensagem.message_id)
    except Forbidden:
        return ResultadoEnvio(erro="bloqueado")
    except RetryAfter:
        return ResultadoEnvio(erro="limite")
    except TimedOut:
        return ResultadoEnvio(erro="incerto")
    except NetworkError:
        return ResultadoEnvio(erro="rede")
    except TelegramError:
        logger.warning("Falha na tela Telegram", exc_info=False)
        return ResultadoEnvio(erro="telegram")
