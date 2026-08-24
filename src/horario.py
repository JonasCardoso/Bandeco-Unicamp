"""Consulta de horários de funcionamento dos restaurantes.

Este módulo fornece funções para consultar os horários de funcionamento
dos restaurantes universitários através da página web.
"""

from typing import Optional

import requests
from bs4 import BeautifulSoup

from util import get_url_horario, retry


@retry(max_attempts=3, delay=1.0, exceptions=requests.RequestException)
def horario_funcionamento() -> Optional[str]:
    """Recupera os horários de funcionamento dos restaurantes.

    Returns:
        String com os horários formatados ou None em caso de erro.
    """
    try:
        horarios = None
        response = requests.get(get_url_horario(), timeout=10)
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
            print(horarios)
            return horarios

    except requests.RequestException as e:
        print(f"[ERROR] Horario - horario_funcionamento(): {e}")
        return None
