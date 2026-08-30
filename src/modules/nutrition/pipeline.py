"""Pipeline nutricional consolidado TACO + TBCA para cardápios do Bandeco."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from .cache import (
    CACHE_DIR,
    DadosNutricionaisIndisponiveis,
)
from .calculation import (
    processar_cardapio,
)
from .parser import extrair_itens
from .rendering import gerar_imagem_tabela as renderizar_tabela
from .sources import _float

CACHE_TABELA_ARQUIVO = "cache_tabela_nutricional.json"
CACHE_TABELA_TTL_HOURS = 24
logger = logging.getLogger(__name__)

from .matching import (
    PIPELINE_SCHEMA_VERSION,
)


def _hash_cardapio(c):
    return hashlib.sha256(f"{PIPELINE_SCHEMA_VERSION}\n{c.strip()}".encode()).hexdigest()


def _carregar_cache_tabela(chave_cardapio=None):
    try:
        d = json.loads(Path(CACHE_TABELA_ARQUIVO).read_text(encoding="utf-8"))
        if (
            datetime.now() - datetime.fromisoformat(d["timestamp"]) > timedelta(hours=CACHE_TABELA_TTL_HOURS)
            or d.get("pipeline") != PIPELINE_SCHEMA_VERSION
        ):
            return None
        if chave_cardapio is not None and d.get("cardapio_hash") != chave_cardapio:
            return None
        return d.get("dados")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def _salvar_cache_tabela(dados, chave_cardapio=None):
    p = Path(CACHE_TABELA_ARQUIVO)
    t = p.with_suffix(".tmp")
    try:
        t.write_text(
            json.dumps(
                {
                    "timestamp": datetime.now().isoformat(),
                    "pipeline": PIPELINE_SCHEMA_VERSION,
                    "cardapio_hash": chave_cardapio,
                    "dados": dados,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        t.replace(p)
    except OSError:
        t.unlink(missing_ok=True)


COLUNAS_IMAGEM = [
    "Nome",
    "Quantidade",
    "Valor Energético (kcal)",
    "Carboidratos (g)",
    "Proteínas (g)",
    "Gorduras (g)",
    "Fibra (g)",
    "Sódio (mg)",
]


def _fmt(v, n=1):
    return "—" if v is None or pd.isna(v) else f"{float(v):.{n}f}"


def _rotulo_total(t, quantidade_cenarios):
    if quantidade_cenarios == 1:
        return "Total"
    item = str(t.get("cenario", "")).partition("+")[2].strip()
    item = re.sub(r"^refresco\s+de\s+", "", item, flags=re.I)
    rest = str(t.get("restaurantes", "")).strip()
    rest = "" if rest in {"", "todos", "não informado", "nan"} else rest.replace(",", "/")
    if rest:
        return f"Total {rest}" + (f" — {item}" if item else "")
    return f"Total — {item}" if item else "Total"


def _projetar_formato_antigo(r):
    out = [COLUNAS_IMAGEM]
    for (item, rest, _), g in r.componentes.groupby(
        ["item_cardapio", "restaurantes", "grupo_alternativa"], dropna=False, sort=False
    ):
        ok = not g.kcal_est.isna().any()

        def somar_coluna(coluna, grupo=g, completo=ok):
            return float(grupo[coluna].sum()) if completo else None

        unidade = "ml" if g.papel.eq("bebida").any() else "g"
        out.append(
            [
                str(item) + (f" [{rest}]" if rest else ""),
                f"{g.porcao_total_est_g.iloc[0]:.0f}{unidade}",
                _fmt(somar_coluna("kcal_est"), 0),
                _fmt(somar_coluna("carbo_g_est")),
                _fmt(somar_coluna("proteina_g_est")),
                _fmt(somar_coluna("lipidios_g_est")),
                _fmt(somar_coluna("fibra_g_est")),
                _fmt(somar_coluna("sodio_mg_est"), 0),
            ]
        )
    for _, t in r.totais.iterrows():
        out.append(
            [
                _rotulo_total(t, len(r.totais)),
                "-",
                _fmt(t.kcal_est, 0),
                _fmt(t.carbo_g_est),
                _fmt(t.proteina_g_est),
                _fmt(t.lipidios_g_est),
                _fmt(t.fibra_g_est),
                _fmt(t.sodio_mg_est, 0),
            ]
        )
    return out


def filtrar_csv(s):
    rows = [x for x in csv.reader(io.StringIO(s), delimiter=";") if len(x) == 8]
    if not rows:
        return None
    if "Nome" not in rows[0][0]:
        rows.insert(0, COLUNAS_IMAGEM.copy())
    dados = [[x[0].strip(), x[1].strip(), *[str(_float(v) or 0.0) for v in x[2:]]] for x in rows[1:]]
    if not dados:
        return None
    return [
        COLUNAS_IMAGEM,
        *dados,
        [
            "Total",
            "-",
            *[str(round(sum(float(x[i]) for x in dados), 1)) for i in range(2, 8)],
        ],
    ]


def _gerar_imagem_tabela(dados, chave_cardapio=None):
    chave = chave_cardapio or hashlib.sha256(json.dumps(dados, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return renderizar_tabela(dados, CACHE_DIR / "tabelas" / f"{chave}.jpg")


def gerar_tabela_nutricional(cardapio) -> Optional[str]:
    if not extrair_itens(cardapio):
        return None
    h = _hash_cardapio(cardapio)
    cache = _carregar_cache_tabela(h)
    if cache is not None:
        return _gerar_imagem_tabela(cache, h)
    try:
        r = processar_cardapio(cardapio)
    except DadosNutricionaisIndisponiveis:
        return None
    d = _projetar_formato_antigo(r)
    _salvar_cache_tabela(d, h)
    return _gerar_imagem_tabela(d, h)
