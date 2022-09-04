import requests as req
from util import URL_HORARIO
from bs4 import BeautifulSoup


def horarioFuncionamento():
    try:
        horarios = ''
        response = req.get(URL_HORARIO)
        soup = BeautifulSoup(response.text, 'html.parser')
        base = soup.find_all("div", {"class": "entry-content clearfix"})
        base = str(base[0].text).split('Horário de funcionamento do ')[1:]
        for i in base:
            horarios += i.split('Cardápio')[0].strip().replace('*', '') + '\n\n'
        return horarios

    except:
        return None
