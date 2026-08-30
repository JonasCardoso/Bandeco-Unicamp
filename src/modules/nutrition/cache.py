"""Diretórios persistentes e validação de escrita do pipeline."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

CACHE_DIR = Path(".cache_bandeco_nutricao")
TACO_CACHE = CACHE_DIR / "taco_composicao.csv"
TBCA_DIR = CACHE_DIR / "tbca"
TBCA_LOCAL_CACHE = TBCA_DIR / "alimentos.txt"
CATALOGO_DIR = CACHE_DIR / "catalogo"
CATALOGO_REFERENCIAS_PATH = CATALOGO_DIR / "referencias_auto_v9.json"


class DadosNutricionaisIndisponiveis(RuntimeError):
    """Bases, modelos ou diretórios essenciais não estão disponíveis."""


def criar_diretorios_cache() -> None:
    for caminho in (CACHE_DIR, TBCA_DIR, CATALOGO_DIR):
        caminho.mkdir(parents=True, exist_ok=True)


def validar_cache_gravavel() -> None:
    """Cria e testa os diretórios persistentes antes de carregar os modelos."""
    hf_home = Path(os.environ.get("HF_HOME", CACHE_DIR / "huggingface"))
    caminhos = (CACHE_DIR, TBCA_DIR, CATALOGO_DIR, hf_home)
    uid = getattr(os, "getuid", lambda: "indisponível")()

    for caminho in caminhos:
        try:
            caminho.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(prefix=".cache-write-test-", dir=caminho):
                pass
        except OSError as erro:
            raise DadosNutricionaisIndisponiveis(
                f"Diretório de cache não gravável: '{caminho}' (uid={uid}). {erro}"
            ) from erro
