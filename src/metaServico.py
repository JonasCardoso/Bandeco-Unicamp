import requests as req
import json
import ngrokService

from telegram.ext import CallbackContext

from artes import gerarImagemPostagem
from util import INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID, INSTAGRAM_GRAPH_URL

ngrok = ngrokService.Ngrok()


def criar_container(context: CallbackContext, image_scr, carosel, texto, url, log):
    try:
        payload = {
            'image_url': f'{url}/{image_scr}',
            'caption': texto,
            'access_token': INSTAGRAM_ACCESS_TOKEN,
            'is_carousel_item': carosel
        }
        response = req.post(INSTAGRAM_GRAPH_URL + INSTAGRAM_USER_ID + '/media', timeout=5, data=payload)

        if response.status_code == 200:
            return json.loads(response.text)['id']
        else:
            log.adicionarLog(f'criar_container - {0} - Não foi possível criar container do instagram\n{response.text}')

    except Exception as error:
        log.adicionarLog(f'criar_container - {0} - Não foi possível criar container do instagram\n{error}')


def criar_carrossel(context: CallbackContext, ids, texto, log):
    try:
        payload = {
            'children': ids,
            'caption': texto,
            'media_type': 'CAROUSEL',
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        response = req.post(INSTAGRAM_GRAPH_URL + INSTAGRAM_USER_ID + '/media', timeout=5, json=payload)

        if response.status_code == 200:
            return json.loads(response.text)['id']
        else:
            log.adicionarLog(f'criar_carrossel - {0} - Não foi possível criar carrossel do instagram\n{response.text}')

    except Exception as error:
        log.adicionarLog(f'criar_carrossel - {0} - Não foi possível criar carrossel do instagram\n{error}')


def postar_timeline_instagram(context: CallbackContext, creation_id, texto, log):
    try:
        payload = {
            'creation_id': creation_id,
            'caption': texto,
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        response = req.post(INSTAGRAM_GRAPH_URL + INSTAGRAM_USER_ID + '/media_publish', timeout=5, data=payload)

        if response.status_code == 200:
            return
        else:
            log.adicionarLog(f'postar_timeline_instagram - {0} - Não foi possível postar na timeline do instagram\n{response.text}')

    except Exception as error:
        log.adicionarLog(f'postar_timeline_instagram - {0} - Não foi possível postar na timeline do instagram\n{error}')


async def postarInsta(context: CallbackContext, titulo, texto, log):
    url = ngrok.iniciar_servidor(context, log)

    try:
        listaPosts = gerarImagemPostagem(context, titulo, texto, log)
        texto_cardapio = f'{titulo} \n\n{texto}'

        if listaPosts is None:
            return
        if len(listaPosts) == 1:
            id = criar_container(context, listaPosts[0], False, texto_cardapio, url, log)
            postar_timeline_instagram(context, id, texto_cardapio, log)
        else:
            ids = list()
            ids.append(criar_container(context, listaPosts[0], True, texto_cardapio, url, log))
            ids.append(criar_container(context, listaPosts[1], True, texto_cardapio, url, log))
            id = criar_carrossel(context, ids, texto_cardapio, log)
            postar_timeline_instagram(context, id, texto_cardapio, log)

    except Exception as error:
        log.adicionarLog(f'postarInsta - {0} - Não foi possível postar no instagram\n{error}')
        await log.enviarLog(context)

    ngrok.desligar_servidor(context, log)
    return
