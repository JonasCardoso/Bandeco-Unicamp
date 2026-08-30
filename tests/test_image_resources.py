"""Testes dos recursos Pillow compartilhados."""

from PIL import Image

from core.constants import ASSETS_DIR, PATH_FONTE_LATO_BOLD
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
