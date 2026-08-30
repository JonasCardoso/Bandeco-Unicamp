"""Operações pequenas e genéricas de arquivo."""

import json
from typing import Any


def salvar_json(dados: Any, nome: str) -> None:
    """Salva em ``<nome>.json`` uma string contendo JSON válido."""
    with open(f"{nome}.json", "w", encoding="utf-8") as arquivo:
        json.dump(json.loads(dados), arquivo, ensure_ascii=False, indent=4)
