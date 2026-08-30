"""Módulo para consulta dos valores das refeições no site da Prefeitura Universitária."""

import logging
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from core.config import get_url_valor_refeicao_almoco, get_url_valor_refeicao_cafe
from shared.retry import retry

logger = logging.getLogger(__name__)


@retry(max_attempts=3, delay=1.0, exceptions=RequestException)
def _extrair_tabela(url: str) -> Optional[Tuple[str, List[Tuple[str, str]]]]:
    """Extrai a tabela de preços de uma página HTML.

    Args:
        url: URL da página com a tabela de valores.

    Returns:
        Tupla (titulo_da_pagina, lista_de_tuplas(categoria, valor)) ou None.
    """
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Extrai o título da página (h1)
    titulo = ""
    h1 = soup.find("h1")
    if h1:
        titulo = h1.get_text(strip=True)
        # Remove prefixo "Valor da Refeição – " se existir
        if titulo.startswith("Valor da Refeição – "):
            titulo = titulo[len("Valor da Refeição – ") :]

    # Encontra a tabela dentro de figure.wp-block-table
    figura = soup.find("figure", class_="wp-block-table")
    if not figura:
        logger.warning(f"Tabela não encontrada na URL: {url}")
        return None

    tabela = figura.find("table")
    if not tabela:
        logger.warning(f"Tag table não encontrada na URL: {url}")
        return None

    # Extrai todas as linhas, pulando o cabeçalho
    itens = []
    for linha in tabela.find_all("tr"):
        celulas = linha.find_all(["td", "th"])
        if len(celulas) < 2:
            continue

        # Pula a primeira linha (cabeçalho da tabela)
        primeira_categoria = celulas[0].get_text(strip=True)
        if primeira_categoria == "Categoria":
            continue

        categoria = celulas[0].get_text(strip=True)
        valor = celulas[1].get_text(strip=True)
        itens.append((categoria, valor))

    if not itens:
        logger.warning(f"Nenhum item encontrado na tabela da URL: {url}")
        return None

    return (titulo, itens)


def obter_valores_refeicao() -> Optional[str]:
    """Consulta os valores das refeições em ambas as páginas e retorna texto formatado.

    Returns:
        String formatada para mensagem do bot, ou None em caso de erro.
    """
    try:
        resultado_cafe = _extrair_tabela(get_url_valor_refeicao_cafe())
        resultado_almoco = _extrair_tabela(get_url_valor_refeicao_almoco())

        if resultado_cafe is None and resultado_almoco is None:
            logger.error("Falha ao extrair dados de ambas as páginas.")
            return None

        texto = "<b>VALOR DAS REFEIÇÕES</b>\n\n"

        # Adiciona café da manhã
        if resultado_cafe:
            titulo, itens = resultado_cafe
            texto += "<i><b>Café da Manhã</b></i>\n"
            for categoria, valor in itens:
                texto += f"- <b>{categoria}</b>:\n  {valor}\n"
            texto += "\n"

        # Adiciona almoço e jantar
        if resultado_almoco:
            titulo, itens = resultado_almoco
            texto += "<i><b>Almoço e Jantar</b></i>\n"
            for categoria, valor in itens:
                texto += f"- <b>{categoria}</b>:\n  {valor}\n"

        return texto

    except RequestException as e:
        logger.error(f"Erro de requisição ao obter valores das refeições: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao obter valores das refeições: {e}")
        return None
