"""Serviço de integração com Twitter/X via tweetkit_x."""

from telegram.ext import CallbackContext
from tweetkit_x import TweetKit

from core.config import get_tweetkit_cookie

# Cliente Twitter/X — inicializado sob demanda via lazy loading
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
        detalhe = resposta.get("error", resposta) if isinstance(resposta, dict) else resposta
        raise RuntimeError(f"Falha ao publicar no Twitter/X: {detalhe}")
    return resposta


async def postar_tweet(context: CallbackContext, titulo: str, texto: str, log) -> None:
    """Publica um tweet com o cardápio do dia.

    Se o texto contiver 'Observações:', divide em dois tweets:
    o primeiro com o cardápio e o segundo com as observações.

    Args:
        context: Contexto do bot Telegram.
        titulo: Título do tweet (ex: 'Cardápio - Segunda-feira').
        texto: Texto completo do cardápio.
        log: Instância de Log para registro de erros.
    """
    try:
        partes = texto.split("Observações:")
        cliente = _get_client()
        resposta = _validar_resposta(cliente.post(f"{titulo}\n\n{partes[0]}"))
        if len(partes) >= 2:
            _validar_resposta(cliente.post(partes[1], reply_to=resposta["id"]))
    except Exception as error:
        log.adicionar_log(f"postarTweet - {0} - Não foi possível postar o tweet\n{error}")
        await log.enviar_log(context)
