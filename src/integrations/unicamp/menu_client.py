"""Consulta de cardápios do Bandeco Unicamp.

Este módulo fornece funções para consultar os cardápios diários
dos restaurantes universitários através da prefeitura e API JSON.
"""

import logging
from typing import List, Optional

import requests as req
from bs4 import BeautifulSoup

from core.config import get_url_bandeco_json, get_url_bandeco_prefeitura
from shared.retry import retry

logger = logging.getLogger(__name__)


@retry(max_attempts=3, delay=1.0, exceptions=(req.RequestException,))
def _get_prefeitura(url: str):
    return req.get(url, timeout=5)


@retry(max_attempts=3, delay=1.0, exceptions=(req.RequestException,))
def _post_json(url: str):
    return req.post(url, timeout=5)


def comida(data: str) -> Optional[List[str]]:
    """Recupera o cardápio para uma data específica.

    Tenta primeiro pela página da prefeitura e, se falhar,
    tenta a API JSON.

    Args:
        data: Data no formato 'YYYY-MM-DD'.

    Returns:
        Lista de strings com os cardápios ou None em caso de erro.
    """
    cardapios = comida_site_prefeitura(data)
    if cardapios is None:
        cardapios = comida_site_json(data)
    if cardapios is not None:
        siglas = ["ru", "ra", "rs", "hc", "pts", "caism"]
        for id, cardapio in enumerate(cardapios):
            cardapios[id] = abreviacoes(siglas, cardapio)
        return cardapios
    return None


def abreviacoes(siglas: List[str], cardapio: str) -> str:
    """Substitui nomes longos de restaurantes por suas siglas.

    Args:
        siglas: Lista de siglas dos restaurantes.
        cardapio: Texto do cardápio original.

    Returns:
        Cardápio com as abreviações aplicadas.
    """
    for sigla in siglas:
        indices = [i for i in range(len(cardapio)) if cardapio.startswith(sigla, i)]
        for indice in indices:
            if (
                (indice == 0 and not cardapio[indice + len(sigla)].isalpha())
                or (not cardapio[indice - 1].isalpha() and indice + len(sigla) == len(cardapio))
                or (not cardapio[indice - 1].isalpha() and not cardapio[indice + len(sigla)].isalpha())
            ):
                cardapio = cardapio[:indice] + sigla.upper() + cardapio[indice + len(sigla) :]
    return cardapio


def comida_site_prefeitura(data: str) -> Optional[List[str]]:
    """Consulta o cardápio na página da prefeitura.

    Args:
        data: Data no formato 'YYYY-MM-DD'.

    Returns:
        Lista de strings com os cardápios ou None em caso de erro.
    """
    try:
        response = _get_prefeitura(get_url_bandeco_prefeitura() + data)

        if "Não existe cardápio cadastrado no momento !" in response.text or response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        base = soup.find_all("div", {"class": "menu-section"})
        cardapios = list()

        for i in base:
            if "Não há jantar" in i.text or "Não há almoço" in i.text:
                cardapios.append("Refeição não cadastrada.")
                continue
            cardapio = ""
            i = i.find_all("div")
            cardapio += i[1].text.capitalize() + "\n"
            i = i[2].findAll(string=True)
            for j in i:
                if len(j) > 1:
                    cardapio += j.strip().capitalize() + "\n"
                else:
                    cardapio += "\n"
            cardapios.append(cardapio)

        if len(cardapios) == 0:
            return None

        cafe = "Café com leite\nAchocolatado\nPão\nMargarina\nGeleia\nFruta\n\n"
        cardapios.append(cafe)

        return cardapios

    except req.RequestException as e:
        logger.warning("Erro ao consultar cardápio da prefeitura (%s): %s", data, e)
        return None


def comida_site_json(data: str) -> Optional[List[str]]:
    """Consulta o cardápio na API JSON do Bandeco.

    Args:
        data: Data no formato 'YYYY-MM-DD'.

    Returns:
        Lista de strings com os cardápios ou None em caso de erro.
    """
    try:
        response = _post_json(get_url_bandeco_json())
        if "Server-unavailable!" in response.text or "Acesso indevido" in response.text or response.status_code != 200:
            return None

        cardapios = ["Refeição não cadastrada."] * 4
        chaves = ["PRATO_PRINCIPAL", "ACOMPANHAMENTO", "PTS", "GUARNICAO", "SALADA", "SOBREMESA", "BEBIDA", "OBS"]
        refeicoes = ["Almoço", "Almoço Vegano", "Jantar", "Jantar Vegano"]

        for i in response.json()["CARDAPIO"]:
            if i["DATA"] == data:
                posicao = refeicoes.index(i["TIPO"])
                cardapio = ""
                for chave in chaves:
                    if i[chave] == "-" or "não informado" in i[chave]:
                        continue
                    frase = i[chave].replace("\r", "")
                    if chave == chaves[-1]:
                        cardapio += "\n" + "Observações:\n"
                        frases = (
                            frase.replace('<FONT COLOR ="RED">', "\n")
                            .replace("</b>", "")
                            .replace("<b>", "")
                            .split("\n")
                        )
                        for frase in frases:
                            if frase == frases[-1]:
                                cardapio += "\n"
                            if len(frase) >= 1:
                                cardapio += frase.capitalize() + "\n"
                    else:
                        cardapio += frase.capitalize() + "\n"
                cardapios[posicao] = cardapio

        cafe = "Café com leite\nAchocolatado\nPão\nMargarina\nGeleia\nFruta\n\n"
        cardapios.append(cafe)

        return cardapios

    except req.RequestException as e:
        logger.warning("Erro ao consultar cardápio JSON (%s): %s", data, e)
        return None
