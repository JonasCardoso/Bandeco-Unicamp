import datetime as dt
import textwrap

from PIL import Image, ImageDraw, ImageFont

from util import PATH_FONTE_LATO_BOLD, PATH_FONTE_LATO_MEDIUM

IMG_SIZE = 1080


def gerar_titulo(titulo_cardapio, nome_imagem, cor_texto2):
    img = Image.open(f'{nome_imagem}.jpg')
    img_draw = ImageDraw.Draw(img)
    fonte_titulo = ImageFont.truetype(PATH_FONTE_LATO_BOLD, 50)
    wrap_textos = textwrap.wrap(titulo_cardapio.upper(), width=25)
    altura_i = 54 if len(wrap_textos) > 1 else 80
    espacamento_vertical_fonte = 0
    altura_f = altura_i

    for wrap_texto in wrap_textos:
        w, h = fonte_titulo.getsize(wrap_texto)
        img_draw.text(((img.size[0] - w) / 2, altura_f), wrap_texto, font=fonte_titulo, fill=cor_texto2)
        altura_f += h + espacamento_vertical_fonte

    return img


def gerar_data(img, cor_texto2):
    img_draw = ImageDraw.Draw(img)
    fonte_titulo = ImageFont.truetype(PATH_FONTE_LATO_BOLD, 40)
    hoje = dt.datetime.today()
    data = str(hoje.strftime('%d-%m-%Y'))
    altura_i = 972
    w, h = (fonte_titulo.getsize(data))
    img_draw.text(((img.size[0] - w) / 2, altura_i), data, font=fonte_titulo, fill=cor_texto2)

    return img


def pegar_identidade_visual(titulo_cardapio):
    if 'tradicional' in titulo_cardapio.lower():
        pasta = 'vermelho'
        return f'src/{pasta}/img_cardapio', f'src/{pasta}/img_obs', (0, 0, 0), (255, 255, 255), (174, 34, 37)
    elif 'vegetariano' in titulo_cardapio.lower():
        pasta = 'amarelo'
        return f'src/{pasta}/img_cardapio', f'src/{pasta}/img_obs', (0, 0, 0), (0, 0, 0), (212, 115, 53)
    else:
        pasta = 'verde'
        return f'src/{pasta}/img_cardapio', f'src/{pasta}/img_obs', (0, 0, 0), (255, 255, 255), (0, 128, 54)


def gerar_imagem_postagem(titulo_cardapio, texto_cardapio, log):
    try:
        textos_cardapio = texto_cardapio.split('Observações:')
        lista_posts = list()
        nome_imagem_cardapio, nome_image_obs, cor_texto1, cor_texto2, cor_auxiliar = pegar_identidade_visual(
            titulo_cardapio)
        lista_posts.append(
            gerar_imagem_cardapio(titulo_cardapio, textos_cardapio[0], nome_imagem_cardapio, cor_texto1, cor_texto2,
                                  cor_auxiliar))
        if len(textos_cardapio) == 2:
            lista_posts.append(
                gerar_imagem_obs(titulo_cardapio, textos_cardapio[1], nome_image_obs, cor_texto1, cor_texto2))
        return lista_posts

    except Exception as error:
        log.adicionar_log(f'gerar_imagem_postagem - {0} - Não foi possível gerar imagem da postagem\n{error}')
        return None


def gerar_imagem_cardapio(titulo_cardapio, texto_cardapio, nome_imagem, cor_texto1, cor_texto2, cor_auxiliar):
    img = gerar_titulo(titulo_cardapio, nome_imagem, cor_texto2)
    img = gerar_data(img, cor_texto2)
    textos = texto_cardapio.split('\n')
    bolinha = Image.open("src/bolinha.png")
    img_draw = ImageDraw.Draw(img)
    fonte_texto = ImageFont.truetype(PATH_FONTE_LATO_MEDIUM, 40)
    altura_i = 240
    comprimento_fonte_i = 260
    espacamento_vertical_fonte = 6
    comprimento_linha_vertical_i = 290
    comprimento_bolinha_i = 393
    posicao_linha_horizontal = 430
    altura_f = altura_i
    ultima_altura = altura_i
    espacamento_vertical = 20

    for i, texto in enumerate(textos):
        wrap_textos = textwrap.wrap(texto, width=31)
        if len(wrap_textos) == 0:
            continue
        for wrap_texto in wrap_textos:
            w, h = fonte_texto.getsize(wrap_texto)
            img_draw.text(((IMG_SIZE / 2) - comprimento_fonte_i, altura_f), wrap_texto, font=fonte_texto,
                          fill=cor_texto1)
            altura_f += h + espacamento_vertical_fonte

        altura_f += espacamento_vertical
        img_draw.bitmap(((IMG_SIZE / 2) - comprimento_bolinha_i,
                         ((altura_f - ultima_altura - bolinha.size[0]) / 2) + ultima_altura), bolinha,
                        fill=cor_auxiliar)
        if i < len(textos) - 3:
            img_draw.line([((IMG_SIZE / 2) - posicao_linha_horizontal, altura_f),
                           ((IMG_SIZE / 2) + posicao_linha_horizontal, altura_f)], fill=cor_auxiliar, width=3)
        ultima_altura = altura_f
        altura_f += espacamento_vertical

    img_draw.line([((IMG_SIZE / 2) - comprimento_linha_vertical_i, altura_i),
                   ((IMG_SIZE / 2) - comprimento_linha_vertical_i, altura_f - espacamento_vertical)],
                  fill=cor_auxiliar, width=3)

    name = f'{nome_imagem}_post_0.jpg'
    img.save(name)

    return name


def gerar_imagem_obs(titulo_cardapio, texto_cardapio, nome_imagem, cor_texto1, cor_texto2):
    img = gerar_titulo(titulo_cardapio, nome_imagem, cor_texto2)
    img = gerar_data(img, cor_texto2)
    textos = texto_cardapio.split('\n')
    img_draw = ImageDraw.Draw(img)
    fonte_texto = ImageFont.truetype(PATH_FONTE_LATO_MEDIUM, 45)
    altura_i = 250
    espacamento_vertical_fonte = 6

    for j, texto in enumerate(textos):
        wrap_texto = textwrap.wrap(texto, width=30)
        if len(wrap_texto) == 0:
            if j == 0:
                continue
            wrap_texto = [' ']
        for linha in wrap_texto:
            w, h = fonte_texto.getsize(linha)
            img_draw.text(((IMG_SIZE - w) / 2, altura_i), linha, font=fonte_texto, fill=cor_texto1)
            altura_i += h + espacamento_vertical_fonte

    name = f'{nome_imagem}_post_1.jpg'
    img.save(name)

    return name
