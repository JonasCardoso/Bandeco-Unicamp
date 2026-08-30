"""Pipeline nutricional consolidado TACO + TBCA para cardápios do Bandeco."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import re
import threading
import time
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
CACHE_TABELA_MAX_ENTRADAS = 64
logger = logging.getLogger(__name__)
_CACHE_LOCK = threading.RLock()

from .matching import (
    PIPELINE_SCHEMA_VERSION,
)


def _hash_cardapio(c):
    return hashlib.sha256(f"{PIPELINE_SCHEMA_VERSION}\n{c.strip()}".encode()).hexdigest()


def _agora() -> datetime:
    return datetime.now()


def _caminho_imagem(chave_cardapio: str) -> Path:
    return CACHE_DIR / "tabelas" / f"{chave_cardapio}.jpg"


def _ler_cache() -> dict:
    try:
        dados = json.loads(Path(CACHE_TABELA_ARQUIVO).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {"pipeline": PIPELINE_SCHEMA_VERSION, "entradas": {}}
    if "entradas" in dados:
        return dados
    chave = dados.get("cardapio_hash")
    entrada = {"timestamp": dados.get("timestamp"), "dados": dados.get("dados")}
    return {"pipeline": dados.get("pipeline"), "entradas": {chave: entrada} if chave else {}}


def _entrada_valida(entrada: dict, agora: datetime) -> bool:
    try:
        return agora - datetime.fromisoformat(entrada["timestamp"]) <= timedelta(hours=CACHE_TABELA_TTL_HOURS)
    except (KeyError, TypeError, ValueError):
        return False


def _limpar_cache(dados: dict, agora: datetime) -> bool:
    entradas = dados.setdefault("entradas", {})
    removidas = []
    for chave, entrada in list(entradas.items()):
        if not _entrada_valida(entrada, agora):
            removidas.append(chave)
            entradas.pop(chave, None)
    excedentes = max(0, len(entradas) - CACHE_TABELA_MAX_ENTRADAS)
    if excedentes:
        ordenadas = sorted(entradas, key=lambda chave: entradas[chave].get("timestamp", ""))
        for chave in ordenadas[:excedentes]:
            removidas.append(chave)
            entradas.pop(chave, None)
    for chave in removidas:
        _caminho_imagem(chave).unlink(missing_ok=True)
    if removidas:
        logger.info("Cache nutricional: %d entrada(s) removida(s); %d restante(s).", len(removidas), len(entradas))
    return bool(removidas)


def _escrever_cache(dados: dict) -> None:
    p = Path(CACHE_TABELA_ARQUIVO)
    p.parent.mkdir(parents=True, exist_ok=True)
    temporario = p.with_suffix(f"{p.suffix}.{threading.get_ident()}.tmp")
    try:
        temporario.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        temporario.replace(p)
    finally:
        temporario.unlink(missing_ok=True)


def _carregar_cache_tabela(chave_cardapio=None):
    if chave_cardapio is None:
        return None
    with _CACHE_LOCK:
        agora = _agora()
        cache = _ler_cache()
        alterado = cache.get("pipeline") != PIPELINE_SCHEMA_VERSION
        if alterado:
            cache = {"pipeline": PIPELINE_SCHEMA_VERSION, "entradas": {}}
        alterado = _limpar_cache(cache, agora) or alterado
        if alterado:
            _escrever_cache(cache)
        entrada = cache["entradas"].get(chave_cardapio)
        if entrada is None or not _entrada_valida(entrada, agora):
            logger.info("Cache nutricional miss: %s", chave_cardapio[:12])
            return None
        logger.info("Cache nutricional hit: %s", chave_cardapio[:12])
        return entrada.get("dados")


def _salvar_cache_tabela(dados, chave_cardapio=None):
    if chave_cardapio is None:
        return
    with _CACHE_LOCK:
        agora = _agora()
        cache = _ler_cache()
        if cache.get("pipeline") != PIPELINE_SCHEMA_VERSION:
            cache = {"pipeline": PIPELINE_SCHEMA_VERSION, "entradas": {}}
        cache.setdefault("entradas", {})[chave_cardapio] = {"timestamp": agora.isoformat(), "dados": dados}
        _limpar_cache(cache, agora)
        try:
            _escrever_cache(cache)
            logger.info("Cache nutricional salvo: %d entrada(s).", len(cache["entradas"]))
        except OSError:
            logger.warning("Não foi possível persistir o cache nutricional.", exc_info=True)


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
    destino = _caminho_imagem(chave)
    if destino.is_file() and destino.stat().st_size > 0:
        logger.info("Imagem nutricional reutilizada: %s (%d bytes).", chave[:12], destino.stat().st_size)
        return str(destino.with_suffix(""))
    inicio = time.perf_counter()
    resultado = renderizar_tabela(dados, destino)
    logger.info("Imagem nutricional renderizada em %.3fs: %s", time.perf_counter() - inicio, chave[:12])
    return resultado


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
