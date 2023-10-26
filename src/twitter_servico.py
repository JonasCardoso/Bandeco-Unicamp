import tweepy
from telegram.ext import CallbackContext
from util import BEARER_TOKEN_TWITTER, API_KEY_TWITTER, API_KEY_SECRET_TWITTER, ACCESS_TOKEN_TWITTER, \
    ACCESS_TOKEN_SECRET_TWITTER

client = tweepy.Client(bearer_token=BEARER_TOKEN_TWITTER, consumer_key=API_KEY_TWITTER,
                       consumer_secret=API_KEY_SECRET_TWITTER, access_token=ACCESS_TOKEN_TWITTER,
                       access_token_secret=ACCESS_TOKEN_SECRET_TWITTER)


async def postar_tweet(context: CallbackContext, titulo, texto, log):
    try:
        texto = texto.split('Observações:')
        if len(texto) >= 2:
            resposta = client.create_tweet(text=f'{titulo}\n\n{texto[0]}')
            client.create_tweet(text=texto[1], in_reply_to_tweet_id=resposta[0]['id'])
        else:
            client.create_tweet(text=f'{titulo}\n\n{texto[0]}')
    except Exception as error:
        log.adicionar_log(f'postarTweet - {0} - Não foi possível postar o tweet\n{error}')
        await log.enviar_log(context)
