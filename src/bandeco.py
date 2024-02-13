import requests as req
from util import URL_BANDECO_PREFEITURA, URL_BANDECO_JSON
from bs4 import BeautifulSoup


def comida(data):
    cardapios = comida_site_prefeitura(data)
    if cardapios is None:
        cardapios = comida_site_json(data)
    if cardapios is not None:
        siglas = ['ru', 'ra', 'rs', 'hc', 'pts']
        for id, cardapio in enumerate(cardapios):
            cardapios[id] = abreviacoes(siglas, cardapio)
        return cardapios

    return None


def abreviacoes(siglas, cardapio):
    for sigla in siglas:
        indices = [i for i in range(len(cardapio)) if cardapio.startswith(sigla, i)]
        for indice in indices:
            if ((indice == 0 and not cardapio[indice + len(sigla)].isalpha())
                    or (not cardapio[indice - 1].isalpha() and indice + len(sigla) == len(cardapio))
                    or (not cardapio[indice - 1].isalpha() and not cardapio[indice + len(sigla)].isalpha())):
                cardapio = cardapio[:indice] + sigla.upper() + cardapio[indice + len(sigla):]
    return cardapio


def comida_site_prefeitura(data):
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
            cardapio += i[1].text.capitalize() + '\n'
            i = i[2].findAll(string=True)
            for j in i:
                if len(j) > 1:
                    cardapio += j.strip().capitalize() + '\n'
                else:
                    cardapio += '\n'
            cardapios.append(cardapio)

        if len(cardapios) == 0:
            return None

        cafe = 'Café com leite\nAchocolatado\nPão\nMargarina\nGeleia\nFruta\n\n'
        cardapios.append(cafe)

        return cardapios

    except:
        return None


def comida_site_json(data):
    try:
        response = req.post(URL_BANDECO_JSON, timeout=5)
        if 'Server-unavailable!' in response.text or 'Acesso indevido' in response.text or response.status_code != 200:
            return None

        cardapios = list()
        chaves = ['PRATO_PRINCIPAL', 'ACOMPANHAMENTO', 'PTS', 'GUARNICAO', 'SALADA', 'SOBREMESA', 'SUCO', 'OBS']

        for i in response.json()['CARDAPIO']:
            if i['DATA'] == data:
                cardapio = ''
                for chave in chaves:
                    if i[chave] == '-' or 'não informado' in i[chave]:
                        continue
                    frase = i[chave].replace('\r', '')
                    if chave == chaves[-1]:
                        cardapio += '\n' + 'Observações:\n'
                        frases = frase.replace('<FONT COLOR =\"RED\">', '\n').split('\n')
                        for frase in frases:
                            if frase == frases[-1]:
                                cardapio += '\n'
                            if len(frase) >= 1:
                                cardapio += frase.capitalize() + '\n'
                    else:
                        cardapio += frase.capitalize() + '\n'
                cardapios.append(cardapio)

        if len(cardapios) == 0:
            return None

        cafe = 'Café com leite\nPão\nMargarina\nGeleia\nFruta\n\n'
        cardapios.append(cafe)

        return cardapios
    except:
        return None
