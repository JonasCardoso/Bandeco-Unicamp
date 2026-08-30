"""Concorrência, expiração e reutilização do cache nutricional."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from modules.nutrition import pipeline


def configurar_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "CACHE_TABELA_ARQUIVO", str(tmp_path / "cache.json"))
    monkeypatch.setattr(pipeline, "CACHE_DIR", tmp_path)


def test_cache_armazena_varios_cardapios(tmp_path, monkeypatch):
    configurar_cache(tmp_path, monkeypatch)
    pipeline._salvar_cache_tabela([["a"]], "hash-a")
    pipeline._salvar_cache_tabela([["b"]], "hash-b")
    assert pipeline._carregar_cache_tabela("hash-a") == [["a"]]
    assert pipeline._carregar_cache_tabela("hash-b") == [["b"]]


def test_cache_corrompido_e_recuperado(tmp_path, monkeypatch):
    configurar_cache(tmp_path, monkeypatch)
    (tmp_path / "cache.json").write_text("{quebrado", encoding="utf-8")
    assert pipeline._carregar_cache_tabela("hash") is None
    pipeline._salvar_cache_tabela([["ok"]], "hash")
    assert pipeline._carregar_cache_tabela("hash") == [["ok"]]


def test_cache_expirado_remove_dados_e_imagem(tmp_path, monkeypatch):
    configurar_cache(tmp_path, monkeypatch)
    agora = datetime(2026, 8, 30, 12, 0)
    monkeypatch.setattr(pipeline, "_agora", lambda: agora)
    imagem = tmp_path / "tabelas" / "hash.jpg"
    imagem.parent.mkdir()
    imagem.write_bytes(b"jpeg")
    cache = {
        "pipeline": pipeline.PIPELINE_SCHEMA_VERSION,
        "entradas": {
            "hash": {
                "timestamp": (agora - timedelta(hours=25)).isoformat(),
                "dados": [["antigo"]],
            }
        },
    }
    (tmp_path / "cache.json").write_text(json.dumps(cache), encoding="utf-8")
    assert pipeline._carregar_cache_tabela("hash") is None
    assert not imagem.exists()


def test_imagem_pronta_nao_e_renderizada_novamente(tmp_path, monkeypatch):
    configurar_cache(tmp_path, monkeypatch)
    destino = tmp_path / "tabelas" / "hash.jpg"
    destino.parent.mkdir()
    destino.write_bytes(b"jpeg")
    chamadas = []
    monkeypatch.setattr(pipeline, "renderizar_tabela", lambda *_args: chamadas.append(1))
    assert pipeline._gerar_imagem_tabela([["x"]], "hash") == str(destino.with_suffix(""))
    assert chamadas == []


def test_gravacoes_concorrentes_preservam_entradas(tmp_path, monkeypatch):
    configurar_cache(tmp_path, monkeypatch)
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda indice: pipeline._salvar_cache_tabela([[indice]], f"hash-{indice}"), range(16)))
    dados = json.loads((tmp_path / "cache.json").read_text(encoding="utf-8"))
    assert len(dados["entradas"]) == 16


def test_cache_respeita_limite_de_entradas(tmp_path, monkeypatch):
    configurar_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(pipeline, "CACHE_TABELA_MAX_ENTRADAS", 3)
    for indice in range(5):
        pipeline._salvar_cache_tabela([[indice]], f"hash-{indice}")
    dados = json.loads((tmp_path / "cache.json").read_text(encoding="utf-8"))
    assert len(dados["entradas"]) == 3
