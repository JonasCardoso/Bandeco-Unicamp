import datetime as dt
import textwrap

from PIL import Image, ImageDraw, ImageFont
from telegram.ext import CallbackContext

from util import PATH_FONTE_LATO_BOLD, PATH_FONTE_LATO_MEDIUM

IMG_SIZE = 1080


def gerarTitulo(tituloCardapio, nomeImagem, corTexto2):
    img = Image.open(f'{nomeImagem}.jpg')
    imgDraw = ImageDraw.Draw(img)
    fonteTitulo = ImageFont.truetype(PATH_FONTE_LATO_BOLD, 50)
    wrapTextos = textwrap.wrap(tituloCardapio.upper(), width=25)
    alturaI = 54 if len(wrapTextos) > 1 else 80
    espacamentoVerticalFonte = 0
    alturaF = alturaI

    for wrapTexto in wrapTextos:
        w, h = fonteTitulo.getsize(wrapTexto)
        imgDraw.text(((img.size[0] - w) / 2, alturaF), wrapTexto, font=fonteTitulo, fill=corTexto2)
        alturaF += h + espacamentoVerticalFonte

    return img


def gerarData(img, corTexto2):
    imgDraw = ImageDraw.Draw(img)
    fonteTitulo = ImageFont.truetype(PATH_FONTE_LATO_BOLD, 40)
    hoje = dt.datetime.today()
    data = str(hoje.strftime('%d-%m-%Y'))
    alturaI = 972
    w, h = (fonteTitulo.getsize(data))
    imgDraw.text(((img.size[0] - w) / 2, alturaI), data, font=fonteTitulo, fill=corTexto2)

    return img


def pegarIdentidadeVisual(tituloCardapio):
    if 'tradicional' in tituloCardapio.lower():
        pasta = 'vermelho'
        return f'src/{pasta}/img_cardapio', f'src/{pasta}/img_obs', (0, 0, 0), (255, 255, 255), (174, 34, 37)
    elif 'vegetariano' in tituloCardapio.lower():
        pasta = 'amarelo'
        return f'src/{pasta}/img_cardapio', f'src/{pasta}/img_obs', (0, 0, 0), (0, 0, 0), (212, 115, 53)
    else:
        pasta = 'verde'
        return f'src/{pasta}/img_cardapio', f'src/{pasta}/img_obs', (0, 0, 0), (255, 255, 255), (0, 128, 54)


def gerarImagemPostagem(context: CallbackContext, tituloCardapio, textoCardapio, log):
    try:
        textosCardapio = textoCardapio.split('Observações:')
        listaPosts = list()
        nomeImagemCardapio, nomeImageObs, corTexto1, corTexto2, CorAuxiliar = pegarIdentidadeVisual(
            tituloCardapio)
        listaPosts.append(
            gerarImagemCardapio(tituloCardapio, textosCardapio[0], nomeImagemCardapio, corTexto1, corTexto2,
                                CorAuxiliar))
        if len(textosCardapio) == 2:
            listaPosts.append(
                gerarImagemObs(tituloCardapio, textosCardapio[1], nomeImageObs, corTexto1, corTexto2))
        return listaPosts

    except Exception as error:
        log.adicionarLog(f'gerarImagemPostagem - {0} - Não foi possível gerar imagem da postagem\n{error}')
        return None


def gerarImagemCardapio(tituloCardapio, textoCardapio, nomeImagem, corTexto1, corTexto2, CorAuxiliar):
    img = gerarTitulo(tituloCardapio, nomeImagem, corTexto2)
    img = gerarData(img, corTexto2)
    textos = textoCardapio.split('\n')
    bolinha = Image.open("src/bolinha.png")
    imgDraw = ImageDraw.Draw(img)
    fonteTexto = ImageFont.truetype(PATH_FONTE_LATO_MEDIUM, 40)
    alturaI = 240
    comprimentoFonteI = 260
    espacamentoVerticalFonte = 6
    comprimentoLinhaVerticalI = 290
    comprimentoBolinhaI = 393
    posicaoLinhaHorizontal = 430
    alturaF = alturaI
    ultimaAltura = alturaI
    espacamentoVertical = 20

    for i, texto in enumerate(textos):
        wrapTextos = textwrap.wrap(texto, width=31)
        if len(wrapTextos) == 0:
            continue
        for wrapTexto in wrapTextos:
            w, h = fonteTexto.getsize(wrapTexto)
            imgDraw.text(((IMG_SIZE / 2) - comprimentoFonteI, alturaF), wrapTexto, font=fonteTexto,
                         fill=corTexto1)
            alturaF += h + espacamentoVerticalFonte

        alturaF += espacamentoVertical
        imgDraw.bitmap(((IMG_SIZE / 2) - comprimentoBolinhaI,
                        ((alturaF - ultimaAltura - bolinha.size[0]) / 2) + ultimaAltura), bolinha, fill=CorAuxiliar)
        if i < len(textos) - 3:
            imgDraw.line([((IMG_SIZE / 2) - posicaoLinhaHorizontal, alturaF),
                          ((IMG_SIZE / 2) + posicaoLinhaHorizontal, alturaF)], fill=CorAuxiliar, width=3)
        ultimaAltura = alturaF
        alturaF += espacamentoVertical

    imgDraw.line([((IMG_SIZE / 2) - comprimentoLinhaVerticalI, alturaI),
                  ((IMG_SIZE / 2) - comprimentoLinhaVerticalI, alturaF - espacamentoVertical)],
                 fill=CorAuxiliar, width=3)

    name = f'{nomeImagem}_post_0.jpg'
    img.save(name)

    return name


def gerarImagemObs(tituloCardapio, textoCardapio, nomeImagem, corTexto1, corTexto2):
    img = gerarTitulo(tituloCardapio, nomeImagem, corTexto2)
    img = gerarData(img, corTexto2)
    textos = textoCardapio.split('\n')
    imgDraw = ImageDraw.Draw(img)
    fonteTexto = ImageFont.truetype(PATH_FONTE_LATO_MEDIUM, 45)
    alturaI = 250
    espacamentoVerticalFonte = 6

    for j, texto in enumerate(textos):
        wrapTexto = textwrap.wrap(texto, width=30)
        if len(wrapTexto) == 0:
            if j == 0:
                continue
            wrapTexto = [' ']
        for linha in wrapTexto:
            w, h = fonteTexto.getsize(linha)
            imgDraw.text(((IMG_SIZE - w) / 2, alturaI), linha, font=fonteTexto, fill=corTexto1)
            alturaI += h + espacamentoVerticalFonte

    name = f'{nomeImagem}_post_1.jpg'
    img.save(name)

    return name
