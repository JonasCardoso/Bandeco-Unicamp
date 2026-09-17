"""Testes dos recursos Pillow compartilhados."""

import pytest
from PIL import Image

from core.constants import ASSETS_DIR, PATH_FONTE_LATO_BOLD
from presentation import menu_images
from presentation.image_resources import carregar_fonte, copiar_template
from presentation.menu_images import gerar_imagem_postagem


def test_fontes_sao_reutilizadas():
    assert carregar_fonte(PATH_FONTE_LATO_BOLD, 40) is carregar_fonte(PATH_FONTE_LATO_BOLD, 40)


def test_templates_sao_copias_independentes():
    caminho = ASSETS_DIR / "verde" / "img_cardapio.jpg"
    primeira = copiar_template(caminho)
    segunda = copiar_template(caminho)
    try:
        assert primeira.size == segunda.size == (1080, 1080)
        assert primeira is not segunda
        original = segunda.getpixel((0, 0))
        primeira.putpixel((0, 0), (255, 0, 255))
        assert segunda.getpixel((0, 0)) == original
    finally:
        primeira.close()
        segunda.close()


class LogFalso:
    def adicionar_log(self, _mensagem):
        raise AssertionError("A geração não deveria falhar")


@pytest.mark.parametrize(
    "titulo",
    [
        "Almoço Tradicional de Segunda-feira",
        "Jantar Vegano de Segunda-feira",
        "Café da manhã de Segunda-feira",
    ],
)
def test_titulo_de_duas_linhas_preserva_espacamento_legado(monkeypatch, titulo):
    chamadas = []

    class DesenhoFalso:
        def text(self, posicao, texto, *, font, fill):
            chamadas.append((posicao, texto, font, fill))

    monkeypatch.setattr(menu_images, "copiar_template", lambda _caminho: Image.new("RGB", (1080, 1080)))
    monkeypatch.setattr(menu_images.ImageDraw, "Draw", lambda _imagem: DesenhoFalso())

    imagem = menu_images.gerar_titulo(titulo, "template", (255, 255, 255))
    try:
        assert len(chamadas) == 2
        (posicao_1, texto_1, fonte, _), (posicao_2, texto_2, _, _) = chamadas
        bbox_1 = fonte.getbbox(texto_1)
        bbox_2 = fonte.getbbox(texto_2)

        assert posicao_1[1] == 54
        assert posicao_2[1] - posicao_1[1] == bbox_1[3]
        assert posicao_2[1] + bbox_2[1] > posicao_1[1] + bbox_1[3]
        assert posicao_1[0] == (imagem.width - (bbox_1[2] - bbox_1[0])) / 2
        assert posicao_2[0] == (imagem.width - (bbox_2[2] - bbox_2[0])) / 2
    finally:
        imagem.close()


def test_titulo_de_uma_linha_mantem_posicao_inicial(monkeypatch):
    chamadas = []

    class DesenhoFalso:
        def text(self, posicao, texto, *, font, fill):
            chamadas.append((posicao, texto, font, fill))

    monkeypatch.setattr(menu_images, "copiar_template", lambda _caminho: Image.new("RGB", (1080, 1080)))
    monkeypatch.setattr(menu_images.ImageDraw, "Draw", lambda _imagem: DesenhoFalso())

    imagem = menu_images.gerar_titulo("Almoço", "template", (255, 255, 255))
    try:
        assert len(chamadas) == 1
        assert chamadas[0][0][1] == 80
    finally:
        imagem.close()


def test_imagens_geradas_preservam_dimensoes(tmp_path):
    caminhos = gerar_imagem_postagem(
        "Almoço Vegano",
        "ARROZ\nFEIJÃO\nObservações:\nSEM ALTERAÇÕES",
        LogFalso(),
        tmp_path,
    )
    assert caminhos is not None
    assert len(caminhos) == 2
    for caminho in caminhos:
        with Image.open(caminho) as imagem:
            assert imagem.size == (1080, 1080)
