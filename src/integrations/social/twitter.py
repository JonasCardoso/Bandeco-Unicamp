"""Serviço de integração com Twitter/X via tweetkit_x."""

import asyncio

from telegram.ext import CallbackContext
from tweetkit_x import TweetKit

from core.config import get_tweetkit_cookie
from interfaces.telegram.logging import LogLevel, sanitizar_texto

_client = None


def _get_client() -> TweetKit:
    """Retorna o cliente Twitter/X, criando-o sob demanda."""
    global _client
    if _client is None:
        _client = TweetKit(cookie=get_tweetkit_cookie())
    return _client


def _validar_resposta(resposta: dict) -> dict:
    """Retorna uma resposta bem-sucedida ou converte a falha em exceção."""
    if not isinstance(resposta, dict) or not resposta.get("ok"):
        detalhe = resposta.get("error", "resposta inválida") if isinstance(resposta, dict) else "resposta inválida"
        raise RuntimeError(f"Falha ao publicar no Twitter/X: {sanitizar_texto(detalhe)}")
    return resposta


def _postar_tweet_sync(titulo: str, texto: str) -> None:
    partes = texto.split("Observações:")
    cliente = _get_client()
    resposta = _validar_resposta(cliente.post(f"{titulo}\n\n{partes[0]}"))
    if len(partes) >= 2:
        _validar_resposta(cliente.post(partes[1], reply_to=resposta["id"]))


async def postar_tweet(context: CallbackContext, titulo: str, texto: str, log) -> None:
    """Publica texto ou thread sem bloquear o event loop."""
    global _client
    try:
        await asyncio.to_thread(_postar_tweet_sync, titulo, texto)
    except Exception as error:
        _client = None
        log.adicionar_log(
            f"Não foi possível postar no Twitter/X: {sanitizar_texto(error)}",
            LogLevel.ERROR,
            component="twitter",
            event="publish_failed",
        )
        await log.enviar_log(context)
