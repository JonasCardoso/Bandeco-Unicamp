"""Renderização concorrente e atômica da tabela nutricional."""

from __future__ import annotations

import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageOps


def gerar_imagem_tabela(dados: list, destino: Path) -> str:
    """Renderiza em temporários únicos e publica a imagem atomicamente."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporarios: list[Path] = []
    try:
        for _ in range(2):
            arquivo = tempfile.NamedTemporaryFile(suffix=".jpg", dir=destino.parent, delete=False)
            arquivo.close()
            temporarios.append(Path(arquivo.name))
        bruto, final = temporarios

        fig, ax = plt.subplots(figsize=(14, max(4, 0.45 * len(dados))))
        try:
            tabela = ax.table(cellText=dados, loc="center", cellLoc="center")
            tabela.auto_set_font_size(False)
            tabela.set_fontsize(8)
            tabela.auto_set_column_width(col=list(range(8)))
            ax.axis("off")
            fig.savefig(bruto, bbox_inches="tight", pad_inches=0.05, dpi=160)
        finally:
            plt.close(fig)

        with Image.open(bruto) as imagem:
            imagem.load()
            rgb = imagem.convert("RGB")
            caixa = ImageOps.invert(rgb).getbbox()
            (rgb.crop(tuple(np.asarray(caixa))) if caixa else rgb).save(final)
        final.replace(destino)
        return str(destino.with_suffix(""))
    finally:
        for temporario in temporarios:
            temporario.unlink(missing_ok=True)
