import requests as req
from util import URL_BANDECO_PREFEITURA, URL_BANDECO_JSON
from bs4 import BeautifulSoup


def comida(data):
    cardapios = comidaSitePrefeitura(data)
    if cardapios is None:
        cardapios = comidaSiteJson(data)
    return cardapios


def comidaSitePrefeitura(data):
    try:
        response = req.get(URL_BANDECO_PREFEITURA + data, timeout=5)

        if 'Não existe cardápio cadastrado no momento !' in response.text or response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        base = soup.find_all("div", {"class": "menu-section"})
        cardapios = list()

        for i in base:
            cardapio = ''
            i = i.find_all("div")
            cardapio += i[1].text + '\n'
            i = i[2].findAll(text=True)
            for j in i:
                cardapio += j.strip() + '\n'
            cardapios.append(cardapio[0:-4])
            
        if len(cardapios) == 0:
          return None

        cafe = 'Café com leite\nAchocolatado\nPão\nMargarina\nGeleia\nFruta\n\n'
        cardapios.append(cafe)

        return cardapios

    except:
        return None


def comidaSiteJson(data):
    response = req.post(URL_BANDECO_JSON, timeout=5)

    if 'Server-unavailable!' in response.text or 'Acesso indevido' in response.text or response.status_code != 200:
        return None

    cardapios = list()
    chaves = ['PRATO_PRINCIPAL', 'ACOMPANHAMENTO', 'PTS', 'GUARNICAO', 'SALADA', 'SOBREMESA', 'SUCO', 'OBS']

    for i in response.json()['CARDAPIO']:
        if i['DATA'] == data:
            cardapio = ''
            for chave in chaves:
                if i[chave] == '-':
                    continue
                if chave == chaves[-1]:
                    cardapio += '\n' + 'Observações:\n'
                    cardapio += i[chave].replace('\r', '').replace('<FONT COLOR =\"RED\">', '\n')
                else:
                    cardapio += i[chave].replace('\r', '') + '\n'

            cardapios.append(cardapio)
            
    if len(cardapios) == 0:
      return None

    cafe = 'Café com leite\nPão\nMargarina\nGeleia\nFruta\n\n'
    cardapios.append(cafe)

    return cardapios
