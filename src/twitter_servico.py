"""Serviço de integração com Twitter/X.

Este módulo fornece funções para postar tweets sobre os cardápios
do Bandeco Unicamp através da API v2 do Twitter.
"""

import tweepy
from telegram.ext import CallbackContext

from util import (
    get_access_token_secret_twitter,
    get_access_token_twitter,
    get_api_key_secret_twitter,
    get_api_key_twitter,
    get_bearer_token_twitter,
)

# Cliente Twitter/X — inicializado sob demanda via lazy loading
_client = None


def _get_client() -> tweepy.Client:
    """Retorna o cliente Twitter/X, criando-o sob demanda."""
    global _client
    if _client is None:
        _client = tweepy.Client(
            bearer_token=get_bearer_token_twitter(),
            consumer_key=get_api_key_twitter(),
            consumer_secret=get_api_key_secret_twitter(),
            access_token=get_access_token_twitter(),
            access_token_secret=get_access_token_secret_twitter(),
        )
    return _client


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
        partes = texto.split('Observações:')
        if len(partes) >= 2:
            resposta = _get_client().create_tweet(text=f'{titulo}\n\n{partes[0]}')
            _get_client().create_tweet(text=partes[1], in_reply_to_tweet_id=resposta[0]['id'])
        else:
            _get_client().create_tweet(text=f'{titulo}\n\n{partes[0]}')
    except Exception as error:
        log.adicionar_log(f'postarTweet - {0} - Não foi possível postar o tweet\n{error}')
        await log.enviar_log(context)
