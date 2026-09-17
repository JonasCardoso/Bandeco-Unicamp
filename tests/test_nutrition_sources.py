"""Testes das fontes locais e remotas TACO/TBCA."""

import json
from unittest.mock import MagicMock

import pytest
import requests

from modules.nutrition import sources
from modules.nutrition.cache import DadosNutricionaisIndisponiveis


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [(None, None), ("-", None), ("TR", 0.00001), ("1.234,5", 1234.5), (2, 2.0), ("x", None)],
)
def test_float_normaliza_valores(entrada, esperado):
    assert sources._float(entrada) == esperado


def test_carregar_taco_baixa_e_parseia_cache(tmp_path, monkeypatch):
    cache = tmp_path / "taco.csv"
    response = MagicMock(
        content=(b"numero_alimento,descricao,energia_kcal,proteina_g\n1,Arroz cozido,128,2.5\n2,,10,1\n")
    )
    monkeypatch.setattr(sources, "TACO_CACHE", cache)
    monkeypatch.setattr(sources, "criar_diretorios_cache", lambda: None)
    monkeypatch.setattr(sources.requests, "get", lambda *args, **kwargs: response)
    alimentos = sources.carregar_taco()
    esperado = sources._nut_vazio()
    esperado.update(energia_kcal=128.0, proteina_g=2.5)
    assert alimentos == [{"codigo": "1", "nome": "Arroz cozido", "fonte": "TACO", "nutrientes": esperado}]
    assert cache.exists()
    response.raise_for_status.assert_called_once_with()


def test_carregar_taco_converte_erro_de_rede(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "TACO_CACHE", tmp_path / "taco.csv")
    monkeypatch.setattr(sources, "criar_diretorios_cache", lambda: None)

    def falhar(*_args, **_kwargs):
        raise requests.RequestException("offline")

    monkeypatch.setattr(sources.requests, "get", falhar)
    with pytest.raises(DadosNutricionaisIndisponiveis, match="offline"):
        sources.carregar_taco()


def test_baixar_tbca_reutiliza_cache(tmp_path, monkeypatch):
    cache = tmp_path / "tbca.jsonl"
    cache.write_text("já existe", encoding="utf-8")
    monkeypatch.setattr(sources, "TBCA_LOCAL_CACHE", cache)
    get = MagicMock()
    monkeypatch.setattr(sources.requests, "get", get)
    assert sources.baixar_tbca_local() == cache
    get.assert_not_called()


def test_baixar_tbca_baixa_atomicamente(tmp_path, monkeypatch):
    cache = tmp_path / "tbca.jsonl"
    response = MagicMock(content=b'{"descricao": "Arroz"}\n')
    monkeypatch.setattr(sources, "TBCA_LOCAL_CACHE", cache)
    monkeypatch.setattr(sources, "criar_diretorios_cache", lambda: None)
    monkeypatch.setattr(sources.requests, "get", lambda *args, **kwargs: response)
    assert sources.baixar_tbca_local() == cache
    assert cache.read_bytes() == response.content
    response.raise_for_status.assert_called_once_with()


def test_carregar_tbca_ignora_linha_invalida(tmp_path, monkeypatch):
    cache = tmp_path / "tbca.jsonl"
    alimento = {
        "codigo": "B1",
        "descricao": "Feijão cozido",
        "nutrientes": [
            {"Componente": "Proteína", "Unidades": "g", "Valor por 100g": "4,8"},
            {"Componente": "Sódio", "Unidades": "mg", "Valor por 100g": "2"},
        ],
    }
    cache.write_text("inválido\n" + json.dumps(alimento) + "\n", encoding="utf-8")
    monkeypatch.setattr(sources, "baixar_tbca_local", lambda: cache)
    resultado = sources.carregar_tbca_local()
    assert len(resultado) == 1
    assert resultado[0]["codigo"] == "B1"
    assert resultado[0]["nutrientes"]["proteina_g"] == 4.8
    assert resultado[0]["nutrientes"]["sodio_mg"] == 2.0
