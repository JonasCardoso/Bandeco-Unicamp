"""Recursos gráficos compartilhados, carregados uma única vez."""

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageFont

from core.constants import ASSETS_DIR


@lru_cache(maxsize=8)
def carregar_fonte(caminho: str | Path, tamanho: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(caminho, tamanho)


@lru_cache(maxsize=8)
def _carregar_template(caminho: str) -> Image.Image:
    with Image.open(caminho) as imagem:
        imagem.load()
        return imagem.copy()


def copiar_template(caminho: str | Path) -> Image.Image:
    return _carregar_template(str(caminho)).copy()


@lru_cache(maxsize=1)
def carregar_marcador() -> Image.Image:
    with Image.open(ASSETS_DIR / "bolinha.png") as imagem:
        imagem.load()
        return imagem.copy()
