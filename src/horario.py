import requests as req
from util import URL_HORARIO
from bs4 import BeautifulSoup


def horario_funcionamento():
    try:
        horarios = None
        response = req.get(URL_HORARIO)
        soup = BeautifulSoup(response.text, 'html.parser')

        h5_element = soup.find(id="qual-o-horario-de-funcionamento-e-endereco-dos-restaurantes")

        if h5_element:
            faq_container = h5_element.find_parent('div', class_='block-faq')
            if faq_container:
                answer_div = faq_container.find('div', class_='block-faq__faq-answer')
                if answer_div:
                    list_items = answer_div.find_all('li')
                    horarios = '\n'.join([li.get_text(strip=True, separator=' ').replace('*','').replace('  .','.\n') for li in list_items[:3]])
        if  horarios is not None:
            print(horarios)
            return horarios

    except:
        return None
