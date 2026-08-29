"""Consulta de horários de funcionamento dos restaurantes.

Este módulo fornece funções para consultar os horários de funcionamento
dos restaurantes universitários através da página web.
"""

import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

from util import get_url_horario, retry

logger = logging.getLogger(__name__)


@retry(max_attempts=3, delay=1.0, exceptions=(requests.RequestException,))
def _get_horario(url: str):
    return requests.get(url, timeout=10)


def horario_funcionamento() -> Optional[str]:
    """Recupera os horários de funcionamento dos restaurantes.

    Returns:
        String com os horários formatados ou None em caso de erro.
    """
    try:
        horarios = None
        response = _get_horario(get_url_horario())
        if isinstance(response.status_code, int) and response.status_code >= 400:
            return None
        soup = BeautifulSoup(response.text, "html.parser")

        h5_element = soup.find(id="qual-o-horario-de-funcionamento-e-endereco-dos-restaurantes")

        if h5_element:
            faq_container = h5_element.find_parent("div", class_="block-faq")
            if faq_container:
                answer_div = faq_container.find("div", class_="block-faq__faq-answer")
                if answer_div:
                    list_items = answer_div.find_all("li")
                    horarios = "\n".join(
                        [
                            li.get_text(strip=True, separator=" ").replace("*", "").replace("  .", ".\n")
                            for li in list_items[:3]
                        ]
                    )
        if horarios is not None:
            return horarios

    except requests.RequestException as e:
        logger.warning("Falha ao consultar horários: %s", e)
        return None
