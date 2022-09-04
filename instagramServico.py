import datetime as dt
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont
from instagrapi import Client
from instagrapi.story import StoryBuilder
from instagrapi.types import StoryMedia
from telegram.ext import CallbackContext

from util import INSTAGRAM_USERNAME, INSTAGRAM_SENHA


def gerarTitulo(tituloCardapio, nomeImagem, corTexto2):
    img = Image.open(f'{nomeImagem}.jpg')
    imgDraw = ImageDraw.Draw(img)
    fonteTitulo = ImageFont.truetype('Lato-Bold.ttf', 50)
    wrapTextos = textwrap.wrap(tituloCardapio.upper(), width=25)
    alturaI = 54
    espacamentoVerticalFonte = 0
    alturaF = alturaI

    for wrapTexto in wrapTextos:
        w, h = imgDraw.textsize(wrapTexto, font=fonteTitulo)
        imgDraw.text(((img.size[0] - w) / 2, alturaF), wrapTexto, font=fonteTitulo, fill=corTexto2)
        alturaF += h + espacamentoVerticalFonte

    return img


def gerarData(img, corTexto2):
    imgDraw = ImageDraw.Draw(img)
    fonteTitulo = ImageFont.truetype('Lato-Bold.ttf', 40)
    hoje = dt.datetime.today()
    data = str(hoje.strftime('%d-%m-%Y'))
    alturaI = 972
    w, h = imgDraw.textsize(data, font=fonteTitulo)
    imgDraw.text(((img.size[0] - w) / 2, alturaI), data, font=fonteTitulo, fill=corTexto2)

    return img


def pegarIdentidadeVisual(tituloCardapio):
    if 'tradicional' in tituloCardapio.lower():
        pasta = 'vermelho'
        return f'{pasta}/img_cardapio', f'{pasta}/img_obs', (0, 0, 0), (255, 255, 255), (174, 34, 37)
    elif 'vegetariano' in tituloCardapio.lower():
        pasta = 'amarelo'
        return f'{pasta}/img_cardapio', f'{pasta}/img_obs', (0, 0, 0), (0, 0, 0), (212, 115, 53)
    else:
        pasta = 'verde'
        return f'{pasta}/img_cardapio', f'{pasta}/img_obs', (0, 0, 0), (255, 255, 255), (0, 128, 54)


class Instagram:
    client = Client()
    logou = False
    IMG_SIZE = 1080

    def loginInsta(self, context: CallbackContext, log):
        try:
            if not os.path.exists('insta.json'):
                self.client.login(INSTAGRAM_USERNAME, INSTAGRAM_SENHA, relogin=True)
                self.client.dump_settings('insta.json')
            else:
                self.client.load_settings('insta.json')
                self.client.login(INSTAGRAM_USERNAME, INSTAGRAM_SENHA, relogin=True)
            self.logou = True

        except Exception as error:
            log.adicionarLog(f'loginInsta - {0} - Não foi possível logar no instagram\n{error}')
            log.enviarLog(context)

    def postarInsta(self, context: CallbackContext, titulo, texto, log):
        try:
            if not self.logou:
                self.loginInsta(context, log)

            listaPosts = self.gerarImagemPostagem(context, titulo, texto, log)
            if listaPosts is None:
                return
            if len(listaPosts) == 1:
                media = self.client.photo_upload(listaPosts[0], f'{titulo} \n\n{texto}')
            else:
                media = self.client.album_upload(listaPosts, f'{titulo} \n\n{texto}')

            code = media.dict()['code']
            url = f'https://www.instagram.com/p/{code}/'
            media_pk = self.client.media_pk_from_url(url)
            buildout = StoryBuilder(listaPosts[0], bgpath=listaPosts[0].replace('img_cardapio_post_0', 'fundo')).photo(
                5)
            self.client.video_upload_to_story(path=buildout.path, medias=[
                StoryMedia(media_pk=media_pk, x=0.5, y=0.5, width=0.6, height=0.8)])

        except Exception as error:
            log.adicionarLog(f'postarInsta - {0} - Não foi possível postar no instagram\n{error}')
            log.enviarLog(context)

    def gerarImagemPostagem(self, context: CallbackContext, tituloCardapio, textoCardapio, log):
        try:
            textosCardapio = textoCardapio.split('Observações:')
            listaPosts = list()
            nomeImagemCardapio, nomeImageObs, corTexto1, corTexto2, CorAuxiliar = pegarIdentidadeVisual(
                tituloCardapio)
            listaPosts.append(
                self.gerarImagemCardapio(tituloCardapio, textosCardapio[0], nomeImagemCardapio, corTexto1, corTexto2,
                                         CorAuxiliar))
            if len(textosCardapio) == 2:
                listaPosts.append(
                    self.gerarImagemObs(tituloCardapio, textosCardapio[1], nomeImageObs, corTexto1, corTexto2))
            return listaPosts

        except Exception as error:
            log.adicionarLog(f'gerarImagemPostagem - {0} - Não foi possível gear imagem da postagem\n{error}')
            log.enviarLog(context)
            return None

    def gerarImagemCardapio(self, tituloCardapio, textoCardapio, nomeImagem, corTexto1, corTexto2, CorAuxiliar):
        img = gerarTitulo(tituloCardapio, nomeImagem, corTexto2)
        img = gerarData(img, corTexto2)
        textos = textoCardapio.split('\n')
        bolinha = Image.open("bolinha.png")
        imgDraw = ImageDraw.Draw(img)
        fonteTexto = ImageFont.truetype('Lato-Medium.ttf', 40)
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
                w, h = imgDraw.textsize(wrapTexto, font=fonteTexto)
                imgDraw.text(((self.IMG_SIZE / 2) - comprimentoFonteI, alturaF), wrapTexto, font=fonteTexto,
                             fill=corTexto1)
                alturaF += h + espacamentoVerticalFonte

            alturaF += espacamentoVertical
            imgDraw.bitmap(((self.IMG_SIZE / 2) - comprimentoBolinhaI,
                            ((alturaF - ultimaAltura - bolinha.size[0]) / 2) + ultimaAltura), bolinha, fill=CorAuxiliar)
            if i < len(textos) - 3:
                imgDraw.line([((self.IMG_SIZE / 2) - posicaoLinhaHorizontal, alturaF),
                              ((self.IMG_SIZE / 2) + posicaoLinhaHorizontal, alturaF)], fill=CorAuxiliar, width=3)
            ultimaAltura = alturaF
            alturaF += espacamentoVertical

        imgDraw.line([((self.IMG_SIZE / 2) - comprimentoLinhaVerticalI, alturaI),
                      ((self.IMG_SIZE / 2) - comprimentoLinhaVerticalI, alturaF - espacamentoVertical)],
                     fill=CorAuxiliar, width=3)

        name = f'{nomeImagem}_post_0.jpg'
        img.save(name)

        return name

    def gerarImagemObs(self, tituloCardapio, textoCardapio, nomeImagem, corTexto1, corTexto2):
        img = gerarTitulo(tituloCardapio, nomeImagem, corTexto2)
        img = gerarData(img, corTexto2)
        textos = textoCardapio.split('\n')
        imgDraw = ImageDraw.Draw(img)
        fonteTexto = ImageFont.truetype('Lato-Medium.ttf', 45)
        alturaI = 250
        espacamentoVerticalFonte = 6

        for j, texto in enumerate(textos):
            wrapTexto = textwrap.wrap(texto, width=30)
            if len(wrapTexto) == 0:
                if j == 0:
                    continue
                wrapTexto = [' ']
            for linha in wrapTexto:
                w, h = imgDraw.textsize(linha, font=fonteTexto)
                imgDraw.text(((self.IMG_SIZE - w) / 2, alturaI), linha, font=fonteTexto, fill=corTexto1)
                alturaI += h + espacamentoVerticalFonte

        name = f'{nomeImagem}_post_1.jpg'
        img.save(name)

        return name
