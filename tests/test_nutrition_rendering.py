"""Regressões da publicação atômica das imagens nutricionais."""

from pathlib import Path
from unittest.mock import MagicMock

from modules.nutrition import rendering


def test_gerar_imagem_publica_destino_e_remove_temporarios(tmp_path, monkeypatch):
    bruto = b"imagem jpeg"
    fig = MagicMock()
    ax = MagicMock()
    monkeypatch.setattr(rendering.plt, "subplots", lambda **_kwargs: (fig, ax))
    fig.savefig.side_effect = lambda caminho, **_kwargs: Path(caminho).write_bytes(bruto)
    imagem = MagicMock()
    imagem.__enter__.return_value = imagem
    imagem.convert.return_value = imagem
    imagem.crop.return_value = imagem
    imagem.save.side_effect = lambda caminho: Path(caminho).write_bytes(bruto)
    monkeypatch.setattr(rendering.Image, "open", lambda _caminho: imagem)
    monkeypatch.setattr(rendering.ImageOps, "invert", lambda _imagem: imagem)
    imagem.getbbox.return_value = (0, 0, 1, 1)
    destino = tmp_path / "tabelas" / "cardapio.jpg"
    retorno = rendering.gerar_imagem_tabela([["x"] * 8], destino)
    assert retorno == str(destino.with_suffix(""))
    assert destino.read_bytes() == bruto
    assert list(destino.parent.iterdir()) == [destino]
    rendering.plt.close.assert_called_once_with(fig)
