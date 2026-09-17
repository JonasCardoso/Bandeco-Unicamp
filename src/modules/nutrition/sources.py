"""Carregamento e normalização das bases nutricionais TACO/TBCA."""

from __future__ import annotations

import csv
import json

import pandas as pd
import requests

from .cache import (
    TACO_CACHE,
    TBCA_LOCAL_CACHE,
    DadosNutricionaisIndisponiveis,
    criar_diretorios_cache,
)
from .parser import chave_texto

TACO_CSV_URL = "https://raw.githubusercontent.com/brolesi/taco/main/data/processed/taco/taco_composicao.csv"
TBCA_LOCAL_URL = "https://raw.githubusercontent.com/raul-rznd/web-scraping-tbca/refs/heads/main/alimentos.txt"
NUTRIENTES_CHAVE = (
    "energia_kcal",
    "proteina_g",
    "carboidrato_g",
    "lipideos_g",
    "fibra_g",
    "sodio_mg",
)


def _float(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lower()
    if s in {"", "-", "na", "nan"}:
        return None
    if s in {"tr", "traço", "traco"}:
        return 0.00001
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _nut_vazio():
    return {
        x: None
        for x in (
            *NUTRIENTES_CHAVE,
            "potassio_mg",
            "calcio_mg",
            "ferro_mg",
            "magnesio_mg",
            "vitamina_c_mg",
        )
    }


def carregar_taco():
    criar_diretorios_cache()
    if not TACO_CACHE.exists():
        try:
            r = requests.get(TACO_CSV_URL, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            raise DadosNutricionaisIndisponiveis(str(e)) from e
        t = TACO_CACHE.with_suffix(".tmp")
        t.write_bytes(r.content)
        t.replace(TACO_CACHE)
    out = []
    for n, row in enumerate(csv.DictReader(TACO_CACHE.open(encoding="utf-8")), 1):
        nome = str(row.get("descricao") or "").strip()
        codigo = str(row.get("numero_alimento") or n)
        nut = _nut_vazio()
        for k in nut:
            nut[k] = _float(row.get(k))
        if nome:
            out.append({"codigo": codigo, "nome": nome, "fonte": "TACO", "nutrientes": nut})
    return out


def baixar_tbca_local():
    criar_diretorios_cache()
    if TBCA_LOCAL_CACHE.exists():
        return TBCA_LOCAL_CACHE
    try:
        r = requests.get(TBCA_LOCAL_URL, timeout=120)
        r.raise_for_status()
    except requests.RequestException as e:
        raise DadosNutricionaisIndisponiveis(str(e)) from e
    t = TBCA_LOCAL_CACHE.with_suffix(".tmp")
    t.write_bytes(r.content)
    t.replace(TBCA_LOCAL_CACHE)
    return TBCA_LOCAL_CACHE


def _nut_tbca(orig):
    out = _nut_vazio()
    for x in orig or []:
        n, u = chave_texto(x.get("Componente", "")), str(x.get("Unidades", "")).lower()
        k = None
        if n.startswith("energia") and u == "kcal":
            k = "energia_kcal"
        elif n.startswith("proteina") and u == "g":
            k = "proteina_g"
        elif (n.startswith("lipid") or n.startswith("gordura total")) and u == "g":
            k = "lipideos_g"
        elif n.startswith("carboidrato total") and u == "g":
            k = "carboidrato_g"
        elif n.startswith("fibra alimentar") and u == "g":
            k = "fibra_g"
        elif n == "sodio" and u == "mg":
            k = "sodio_mg"
        if k:
            out[k] = _float(x.get("Valor por 100g"))
    return out


def carregar_tbca_local():
    out = []
    for numero, linha in enumerate(baixar_tbca_local().open(encoding="utf-8", errors="replace"), 1):
        try:
            x = json.loads(linha)
        except json.JSONDecodeError:
            continue
        nome = str(x.get("descricao", "")).strip()
        codigo = str(x.get("codigo", numero))
        if nome:
            out.append(
                {
                    "codigo": codigo,
                    "nome": nome,
                    "fonte": "TBCA",
                    "nutrientes": _nut_tbca(x.get("nutrientes")),
                }
            )
    return out
