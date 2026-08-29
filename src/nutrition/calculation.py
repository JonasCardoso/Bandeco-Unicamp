"""Resolução de referências, porções e totais nutricionais."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .matching import (
    VARIEDADES_FEIJAO,
    _familia,
    _marcador,
    _nome_matching,
    obter_pipeline,
)
from .parser import _relacao_item, chave_texto, extrair_itens
from .sources import NUTRIENTES_CHAVE

COLUNAS_SOMA = [
    f"{nutriente}_{sufixo}"
    for nutriente in ("kcal", "proteina_g", "carbo_g", "lipidios_g", "fibra_g", "sodio_mg")
    for sufixo in ("min", "est", "max")
]


def buscar_referencias_nutricionais(i, pipeline=None):
    p = pipeline or obter_pipeline()
    q = i["consulta_prato_completo"]
    if _marcador(q):
        m = p.buscar_referencia(q, {"papel": i["papel"], "tipo_preparacao": "prato_completo"})
        c = m.get("resultado")
        if c and m["status"] == "aceito" and _marcador(q) in chave_texto(_nome_matching(c["nome"])):
            return {
                "modo_item": "prato_completo",
                "principal": m,
                "ingredientes": [],
                "ingredientes_descritivos": i["relacoes"],
            }
    pr = p.buscar_referencia(i["nucleo"], {"papel": i["papel"], "tipo_preparacao": i.get("tipo_preparacao")})
    ings = [
        {
            "ingrediente": x,
            "tipo_relacao": _relacao_item(i, x),
            "match": p.buscar_referencia(x, {"papel": "ingrediente", "tipo_preparacao": i.get("tipo_preparacao")}),
        }
        for x in i["ingredientes"]
    ]
    return {
        "modo_item": "decomposto",
        "principal": pr,
        "ingredientes": ings,
        "ingredientes_descritivos": [r for r in i["relacoes"] if r["tipo"] == "presenca"],
    }


def _stats(cs):
    cs = [c for c in cs if c.get("nutrientes") and any(c["nutrientes"].get(k) is not None for k in NUTRIENTES_CHAVE)]
    if not cs:
        return None, []
    out = {}
    for k in NUTRIENTES_CHAVE:
        v = [c["nutrientes"][k] for c in cs if c["nutrientes"].get(k) is not None]
        out[k] = {
            "min": min(v) if v else None,
            "estimado": sum(v) / len(v) if v else None,
            "max": max(v) if v else None,
        }
    return out, cs


def _feijoes(p):
    por = {}
    for c in p.base_taco + p.base_tbca:
        n = chave_texto(c["nome"])
        v = next((x for x in VARIEDADES_FEIJAO if x in n), None)
        if (
            n.startswith("feijao ")
            and "cozido" in n
            and v
            and not any(x in n for x in ("tropeiro", "feijoada", "fradinho"))
        ):
            if v not in por or c["fonte"] == "TACO":
                por[v] = c
    return list(por.values())


def resolver_nutricao_match(m, pipeline=None):
    s, c = m["status"], m.get("resultado")
    if c is None:
        return {
            "modo": "indisponivel",
            "estatisticas_100g": None,
            "referencias": [],
            "descricao": s,
        }
    if s == "variedade_desconhecida":
        e, u = _stats(_feijoes(pipeline or obter_pipeline()))
        return {
            "modo": "media_variedades",
            "estatisticas_100g": e,
            "referencias": u,
            "descricao": "média de variedades",
        }
    fam = [x for x in m["candidatos_reranker"] if _familia(x) == _familia(c)]
    e, u = _stats(fam if len(fam) > 1 else [c])
    return {
        "modo": "intervalo_variante" if len(fam) > 1 else "unico",
        "estatisticas_100g": e,
        "referencias": u,
        "descricao": "referência real",
    }


def _faixa(i):
    porcao = 200.0 if i.get("papel") == "bebida" else 100.0
    return {"min": porcao, "estimado": porcao, "max": porcao}


def estimar_porcoes_item(i, modo_item="decomposto"):
    total = _faixa(i)
    if modo_item == "prato_completo" or not i["ingredientes"]:
        return {
            "principal": total,
            "ingredientes": {},
            "porcao_total_g": total,
            "metodo": "faixa_por_papel",
            "proporcoes_conhecidas": True,
        }
    return {
        "principal": None,
        "ingredientes": {x: None for x in i["ingredientes"]},
        "porcao_total_g": total,
        "metodo": "proporcoes_nao_informadas",
        "proporcoes_conhecidas": False,
    }


def _linha(i, comp, papel, porcao, m, p):
    r = resolver_nutricao_match(m, p)
    e = r["estatisticas_100g"]
    d = {
        "item_cardapio": i["texto"],
        "componente": comp,
        "papel": papel,
        "porcao_total_est_g": _faixa(i)["estimado"],
        "status": m["status"] if porcao else "proporcao_desconhecida",
        "status_match": m["status"],
        "referencia": " | ".join(x["nome"] for x in r["referencias"]),
        "fonte": "+".join(sorted({x["fonte"] for x in r["referencias"]})),
        "restaurantes": ",".join(i["restaurantes"] or []),
        "grupo_alternativa": i["grupo_alternativa"] or "",
    }
    mapa = {
        "kcal": "energia_kcal",
        "proteina_g": "proteina_g",
        "carbo_g": "carboidrato_g",
        "lipidios_g": "lipideos_g",
        "fibra_g": "fibra_g",
        "sodio_mg": "sodio_mg",
    }
    for nome, k in mapa.items():
        for s, ss in (("min", "min"), ("est", "estimado"), ("max", "max")):
            d[f"{nome}_{s}"] = None if not e or not porcao or e[k][ss] is None else e[k][ss] * porcao[ss] / 100
    return d


def construir_tabela_componentes(itens, refs, pipeline=None):
    p = pipeline or obter_pipeline()
    out = []
    for i, r in zip(itens, refs, strict=True):
        modo = r["modo_item"]
        po = estimar_porcoes_item(i, modo)
        if modo == "prato_completo":
            out.append(
                _linha(
                    i,
                    i["consulta_prato_completo"],
                    i["papel"],
                    po["porcao_total_g"],
                    r["principal"],
                    p,
                )
            )
            continue
        out.append(_linha(i, i["nucleo"], i["papel"], po["principal"], r["principal"], p))
        infos = {x["ingrediente"]: x for x in r["ingredientes"]}
        for x, v in po["ingredientes"].items():
            out.append(_linha(i, x, infos[x]["tipo_relacao"], v, infos[x]["match"], p))
    return pd.DataFrame(out)


def _somar(df, nome, rest):
    falt = df.loc[df.kcal_est.isna(), "componente"].astype(str).tolist()
    d = {
        "cenario": nome,
        "restaurantes": rest,
        "completo": not falt,
        "componentes_sem_referencia": ", ".join(dict.fromkeys(falt)),
    }
    for c in COLUNAS_SOMA:
        d[c] = float(df[c].dropna().sum()) if len(df[c].dropna()) else None
    return d


def construir_tabela_totais(df):
    if df.empty:
        return pd.DataFrame()
    base = df[df.grupo_alternativa == ""]
    grupos = [g for g in df.grupo_alternativa.unique() if g]
    if not grupos:
        return pd.DataFrame([_somar(base, "Refeição", "todos")])
    out = []
    for g in grupos:
        for (item, rest), v in df[df.grupo_alternativa == g].groupby(
            ["item_cardapio", "restaurantes"], dropna=False, sort=False
        ):
            out.append(_somar(pd.concat([base, v]), f"Refeição + {item}", rest or "não informado"))
    return pd.DataFrame(out)


@dataclass
class ResultadoCardapio:
    itens: list
    referencias_por_item: list
    componentes: pd.DataFrame
    totais: pd.DataFrame


def processar_cardapio(cardapio, pipeline=None):
    itens = extrair_itens(cardapio)
    if not itens:
        return ResultadoCardapio([], [], pd.DataFrame(), pd.DataFrame())
    p = pipeline or obter_pipeline()
    refs = [buscar_referencias_nutricionais(i, p) for i in itens]
    c = construir_tabela_componentes(itens, refs, p)
    return ResultadoCardapio(itens, refs, c, construir_tabela_totais(c))
