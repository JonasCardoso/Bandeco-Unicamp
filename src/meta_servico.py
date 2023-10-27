import requests as req
import json
import ngrok_servico

from telegram.ext import CallbackContext

from artes import gerar_imagem_postagem
from util import FACEBOOK_ACCESS_TOKEN, INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID, FACEBOOK_USER_ID, GRAPH_URL

ngrok = ngrok_servico.Ngrok()


def criar_container_instagram(image_scr, carosel, texto, url, log):
    try:
        payload = {
            'image_url': f'{url}/{image_scr}',
            'caption': texto,
            'access_token': INSTAGRAM_ACCESS_TOKEN,
            'is_carousel_item': carosel
        }
        response = req.post(GRAPH_URL + INSTAGRAM_USER_ID + '/media', timeout=5, data=payload)

        if response.status_code == 200:
            return json.loads(response.text)['id']
        else:
            log.adicionar_log(
                f'criar_container_instagram - {0} - Não foi possível criar container do instagram\n{response.text}')

    except Exception as error:
        log.adicionar_log(f'criar_container_instagram - {0} - Não foi possível criar container do instagram\n{error}')


def criar_carrossel_instagram(ids, texto, log):
    try:
        payload = {
            'children': ids,
            'caption': texto,
            'media_type': 'CAROUSEL',
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        response = req.post(GRAPH_URL + INSTAGRAM_USER_ID + '/media', timeout=5, json=payload)

        if response.status_code == 200:
            return json.loads(response.text)['id']
        else:
            log.adicionar_log(
                f'criar_carrossel_instagram - {0} - Não foi possível criar carrossel do instagram\n{response.text}')

    except Exception as error:
        log.adicionar_log(f'criar_carrossel_instagram - {0} - Não foi possível criar carrossel do instagram\n{error}')


def postar_timeline_instagram(creation_id, texto, log):
    try:
        payload = {
            'creation_id': creation_id,
            'caption': texto,
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        response = req.post(GRAPH_URL + INSTAGRAM_USER_ID + '/media_publish', timeout=5, data=payload)

        if response.status_code == 200:
            return
        else:
            log.adicionar_log(f'postar_timeline_instagram - {0} - Não foi possível postar na timeline do '
                              f'instagram\n{response.text}')

    except Exception as error:
        log.adicionar_log(
            f'postar_timeline_instagram - {0} - Não foi possível postar na timeline do instagram\n{error}')


def postar_timeline_facebook(url, image_scr, texto, log):
    try:
        headers = {
            'Content-Type': 'application/json',
        }

        payload = {
            'url': f'{url}/{image_scr}',
            'message': texto,
            'access_token': FACEBOOK_ACCESS_TOKEN
        }
        response = req.post(GRAPH_URL + FACEBOOK_USER_ID + '/photos', timeout=5, json=payload, headers=headers)

        if response.status_code == 200:
            return
        else:
            log.adicionar_log(f'postar_timeline_facebook - {0} - Não foi possível postar na timeline do '
                              f'facebook\n{response.text}')

    except Exception as error:
        log.adicionar_log(f'postar_timeline_facebook - {0} - Não foi possível postar na timeline do facebook\n{error}')


async def postar_meta(context: CallbackContext, titulo, texto, log):
    url = ngrok.iniciar_servidor(log)
    try:
        lista_posts = gerar_imagem_postagem(titulo, texto, log)
        texto_cardapio = f'{titulo} \n\n{texto}'

        if lista_posts is None:
            return
        if len(lista_posts) == 1:
            id_container = criar_container_instagram(lista_posts[0], False, texto_cardapio, url, log)
            postar_timeline_instagram(id_container, texto_cardapio, log)
            postar_timeline_facebook(url, lista_posts[0], texto_cardapio, log)
        else:
            ids_container = list()
            ids_container.append(criar_container_instagram(lista_posts[0], True, texto_cardapio, url, log))
            ids_container.append(criar_container_instagram(lista_posts[1], True, texto_cardapio, url, log))
            id_carrossel = criar_carrossel_instagram(ids_container, texto_cardapio, log)
            postar_timeline_instagram(id_carrossel, texto_cardapio, log)
            postar_timeline_facebook(url, lista_posts[0], texto_cardapio, log)

    except Exception as error:
        log.adicionar_log(f'postarInsta - {0} - Não foi possível postar no instagram\n{error}')

    ngrok.desligar_servidor(log)
    await log.enviar_log(context)

    return
