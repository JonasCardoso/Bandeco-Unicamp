"""Serviços de integração com Meta (Instagram e Facebook).

Este módulo fornece funções para postar imagens e carrosséis
no Instagram e Facebook através da Graph API.
"""

import json

import requests as req
from telegram.ext import CallbackContext

from core.config import (
    get_facebook_access_token,
    get_facebook_user_id,
    get_graph_url,
    get_instagram_access_token,
    get_instagram_user_id,
)
from presentation.menu_images import gerar_imagem_postagem as _gerar_imagem_artes


def criar_container_instagram(
    image_scr: str,
    carosel: bool,
    texto: str,
    url: str,
    log,
) -> str:
    """Cria um container de mídia no Instagram.

    Args:
        image_scr: Nome do arquivo de imagem.
        carosel: True se for parte de um carrossel.
        texto: Legenda da postagem.
        url: URL base para acesso à imagem.
        log: Instância de Log para registro de erros.

    Returns:
        ID do container criado ou False em caso de erro.
    """
    try:
        payload = {
            "image_url": f"{url}/{image_scr}",
            "caption": texto,
            "access_token": get_instagram_access_token(),
            "is_carousel_item": carosel,
        }
        response = req.post(get_graph_url() + get_instagram_user_id() + "/media", data=payload, timeout=15)

        if response.status_code == 200:
            return json.loads(response.text)["id"]
        else:
            log.adicionar_log(
                f"criar_container_instagram - {0} - Não foi possível criar container do instagram\n{response.text}"
            )

    except Exception as error:
        log.adicionar_log(f"criar_container_instagram - {0} - Não foi possível criar container do instagram\n{error}")

    return False


def criar_carrossel_instagram(ids: list, texto: str, log) -> str:
    """Cria um carrossel no Instagram a partir de containers existentes.

    Args:
        ids: Lista de IDs dos containers de mídia.
        texto: Legenda do carrossel.
        log: Instância de Log para registro de erros.

    Returns:
        ID do carrossel criado ou False em caso de erro.
    """
    try:
        payload = {
            "children": ids,
            "caption": texto,
            "media_type": "CAROUSEL",
            "access_token": get_instagram_access_token(),
        }
        response = req.post(get_graph_url() + get_instagram_user_id() + "/media", json=payload, timeout=15)

        if response.status_code == 200:
            return json.loads(response.text)["id"]
        else:
            log.adicionar_log(
                f"criar_carrossel_instagram - {0} - Não foi possível criar carrossel do instagram\n{response.text}"
            )

    except Exception as error:
        log.adicionar_log(f"criar_carrossel_instagram - {0} - Não foi possível criar carrossel do instagram\n{error}")

    return False


def postar_timeline_instagram(creation_id: str, texto: str, log) -> bool:
    """Publica um container na timeline do Instagram.

    Args:
        creation_id: ID do container criado anteriormente.
        texto: Legenda da postagem.
        log: Instância de Log para registro de erros.

    Returns:
        True se publicado com sucesso, False caso contrário.
    """
    try:
        payload = {"creation_id": creation_id, "caption": texto, "access_token": get_instagram_access_token()}
        response = req.post(get_graph_url() + get_instagram_user_id() + "/media_publish", data=payload, timeout=15)

        if response.status_code == 200:
            return True
        else:
            log.adicionar_log(
                f"postar_timeline_instagram - {0} - Não foi possível postar na timeline do instagram\n{response.text}"
            )

    except Exception as error:
        log.adicionar_log(
            f"postar_timeline_instagram - {0} - Não foi possível postar na timeline do instagram\n{error}"
        )

    return False


def postar_timeline_facebook(url: str, image_scr: str, texto: str, log) -> bool:
    """Publica uma imagem na timeline do Facebook.

    Args:
        url: URL base para acesso à imagem.
        image_scr: Nome do arquivo de imagem.
        texto: Legenda da postagem.
        log: Instância de Log para registro de erros.

    Returns:
        True se publicado com sucesso, False caso contrário.
    """
    try:
        headers = {
            "Content-Type": "application/json",
        }

        payload = {"url": f"{url}/{image_scr}", "message": texto, "access_token": get_facebook_access_token()}
        response = req.post(
            get_graph_url() + get_facebook_user_id() + "/photos", json=payload, headers=headers, timeout=15
        )

        if response.status_code == 200:
            return True
        else:
            log.adicionar_log(
                f"postar_timeline_facebook - {0} - Não foi possível postar na timeline do facebook\n{response.text}"
            )

    except Exception as error:
        log.adicionar_log(f"postar_timeline_facebook - {0} - Não foi possível postar na timeline do facebook\n{error}")

    return False


async def postar_instagram(titulo: str, texto: str, log, url: str) -> None:
    """Posta uma imagem de cardápio no Instagram.

    Args:
        titulo: Título do cardápio (ex: 'Almoço Tradicional').
        texto: Texto completo do cardápio.
        log: Instância de Log para registro de erros.
        url: URL pública do servidor ngrok.
    """
    try:
        container_id = criar_container_instagram("img_cardapio_post_0.jpg", False, titulo, url, log)
        if not container_id:
            return

        postar_timeline_instagram(container_id, titulo, log)

    except Exception as error:
        log.adicionar_log(f"postar_instagram - {0} - Erro ao postar no Instagram\\n{error}")


async def postar_facebook(titulo: str, texto: str, log, url: str) -> None:
    """Posta uma imagem de cardápio no Facebook.

    Args:
        titulo: Título do cardápio (ex: 'Almoço Tradicional').
        texto: Texto completo do cardápio.
        log: Instância de Log para registro de erros.
        url: URL pública do servidor ngrok.
    """
    try:
        postar_timeline_facebook(url, "img_cardapio_post_0.jpg", titulo, log)

    except Exception as error:
        log.adicionar_log(f"postar_facebook - {0} - Erro ao postar no Facebook\\n{error}")


async def postar_meta(context: CallbackContext, titulo: str, texto: str, log, url: str) -> None:
    """Publica o cardápio no Meta (Instagram e Facebook).

    Gera a imagem do cardápio e posta simultaneamente no Instagram e Facebook.

    Args:
        context: Contexto do bot Telegram.
        titulo: Título do cardápio (ex: 'Almoço Tradicional').
        texto: Texto completo do cardápio.
        log: Instância de Log para registro de erros.
        url: URL pública do servidor ngrok.
    """
    imagens = gerar_imagem_postagem(titulo, texto, log)
    if not imagens:
        return

    await postar_instagram(titulo, texto, log, url)
    await postar_facebook(titulo, texto, log, url)


def gerar_imagem_postagem(titulo_cardapio: str, texto_cardapio: str, log) -> list | None:
    """Gera imagens de postagem a partir do cardápio.

    Args:
        titulo_cardapio: Título do cardápio.
        texto_cardapio: Texto completo (pode conter 'Observações:').
        log: Instância de Log para registro de erros.

    Returns:
        Lista com nomes das imagens geradas ou None em caso de erro.
    """
    try:
        imagens = _gerar_imagem_artes(titulo_cardapio, texto_cardapio, log)
        return imagens
    except Exception as error:
        log.adicionar_log(f"gerar_imagem_postagem - {0} - Erro ao gerar imagem\\n{error}")
        return None
