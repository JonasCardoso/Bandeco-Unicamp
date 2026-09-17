"""Normalização e parsing puro de textos de cardápio."""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

SIGLAS_LOCAIS = {"RU", "RA", "RS", "HC", "HE", "COTUCA", "CAISM"}
COMBINACOES_SEPARADAS = {
    "arroz integral e feijao": ["Arroz integral", "Feijão"],
    "arroz e feijao": ["Arroz", "Feijão"],
}
CONDIMENTOS = {
    "paprica",
    "oregano",
    "alho",
    "oleo",
    "oleo de soja",
    "oleo de gergelim",
    "azeite",
    "azeite de oliva",
    "molho de soja",
    "shoyu",
    "salsa",
    "salsinha",
    "cebolinha",
    "vinagre",
}
GENERICOS_EXATOS = {
    "fruta",
    "legumes",
    "legumes refogados",
    "salada mista",
    "salada mista de legumes",
}
FRUTAS = {
    "maca",
    "banana",
    "laranja",
    "mamao",
    "melancia",
    "melao",
    "pera",
    "abacaxi",
    "goiaba",
    "tangerina",
    "uva",
    "manga",
    "pessego",
}
PREPARACOES_NOMEADAS = {
    "strogonoff",
    "estrogonofe",
    "quibe",
    "kibe",
    "torta",
    "escondidinho",
    "moqueca",
    "fricasse",
    "cuscuz",
    "polenta",
    "macarrao",
    "lasanha",
    "risoto",
    "omelete",
    "almondega",
    "nuggets",
    "gratinado",
    "pure",
    "creme",
    "virado",
}


def remover_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def expandir_abreviacoes(t):
    t = re.sub(
        r"\bPTS\s*\(\s*PROTE[ÍI]NA\s+TEXTURIZADA\s+DE\s+SOJA\s*\)",
        "proteína texturizada de soja",
        t,
        flags=re.I,
    )
    return re.sub(r"\bpts\b", "proteína texturizada de soja", t, flags=re.I)


def normalizar(t):
    return re.sub(r"\s+", " ", expandir_abreviacoes(str(t)).lower().replace("*", "")).strip()


def chave_texto(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", remover_acentos(normalizar(t)))).strip()


def _dedup(xs: Iterable[str]):
    out = []
    seen = set()
    for x in xs:
        x = x.strip(" ,;:-.")
        k = chave_texto(x)
        if k and k not in seen:
            seen.add(k)
            out.append(x)
    return out


def _lista(t):
    return _dedup(
        re.split(
            r"\s*,\s*|\s+e\s+",
            re.sub(r"^com\s+", "", t.strip(), flags=re.I),
            flags=re.I,
        )
    )


def _locais(t):
    return [x.strip().upper() for x in re.split(r"[/,]", re.sub(r"\s+e\s+", ",", t, flags=re.I)) if x.strip()]


def _so_locais(t):
    x = _locais(t)
    return bool(x) and all(v in SIGLAS_LOCAIS for v in x)


def aglutinar_semantica(texto):
    n = normalizar(texto)
    rel = []
    for c in re.findall(r"\(([^()]*)\)", n):
        if not c.strip() or _so_locais(c):
            continue
        pres = chave_texto(c).startswith(("contem ", "pode conter "))
        limpo = re.sub(r"^(?:cont[eé]m|pode conter)\s+", "", c, flags=re.I) if pres else c
        for v in _lista(limpo):
            rel.append(
                {
                    "tipo": "presenca" if pres else "condimento" if chave_texto(v) in CONDIMENTOS else "componente",
                    "valor": v,
                    "origem": "parenteses",
                }
            )
    principal = re.sub(r"\s+", " ", re.sub(r"\([^()]*\)", " ", n)).strip(" ,.")
    consulta = principal
    partes = re.split(r"\s+com\s+", principal, maxsplit=1, flags=re.I)
    nucleo = partes[0].strip()
    if len(partes) == 2:
        for v in _lista(partes[1]):
            rel.append(
                {
                    "tipo": "condimento" if chave_texto(v) in CONDIMENTOS else "componente",
                    "valor": v,
                    "origem": "com",
                }
            )
    tipo = None
    if chave_texto(nucleo).startswith("salada de "):
        nucleo = re.sub(r"^salada\s+de\s+", "", nucleo, flags=re.I).strip()
        tipo = "salada"
    if "ao alho e oleo" in chave_texto(principal):
        rel += [
            {"tipo": "condimento", "valor": "alho", "origem": "preparo"},
            {"tipo": "condimento", "valor": "óleo", "origem": "preparo"},
        ]
    prioridade = {"presenca": 0, "condimento": 1, "componente": 2}
    u = {}
    for r in rel:
        k = chave_texto(r["valor"])
        if k and (k not in u or prioridade[r["tipo"]] > prioridade[u[k]["tipo"]]):
            u[k] = r
    rel = list(u.values())
    ings = _dedup(
        r["valor"]
        for r in rel
        if r["tipo"] in {"componente", "condimento"} and chave_texto(r["valor"]) != chave_texto(nucleo)
    )
    return {
        "texto_original": texto,
        "texto_normalizado": n,
        "consulta_prato_completo": consulta,
        "nucleo": nucleo,
        "ingredientes": ings,
        "relacoes": rel,
        "tipo_preparacao": tipo,
        "texto_contexto": " ".join([nucleo, *ings]),
    }


def _split_barra(t):
    out = []
    cur = []
    nivel = 0
    for c in t:
        if c == "(":
            nivel += 1
        elif c == ")" and nivel:
            nivel -= 1
        if c == "/" and not nivel:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
    out.append("".join(cur).strip())
    return [x for x in out if x]


def _variante(p):
    m = re.match(r"(.+?)\s*\(([^()]+)\)\)*$", p.strip())
    return (m.group(1).strip(), _locais(m.group(2))) if m and _so_locais(m.group(2)) else (p.strip(), None)


def _item(t, rest=None, g=None):
    i = aglutinar_semantica(t)
    i.update(texto=t.strip(), restaurantes=rest, grupo_alternativa=g)
    return i


def _titulo(t):
    return bool(re.match(r"^(?:almoço|jantar|café\s+da\s+manhã)\b", t, re.I))


def _papel(i, n):
    q = chave_texto(i["nucleo"])
    if "refresco" in q or q.startswith("suco "):
        return "bebida"
    if q.startswith("arroz"):
        return "arroz"
    if q == "feijao":
        return "feijao"
    if i.get("tipo_preparacao") == "salada" or chave_texto(i["texto"]).startswith("salada "):
        return "salada"
    if (
        q == "fruta"
        or q in FRUTAS
        or any(
            x in q
            for x in (
                "goiabada",
                "doce",
                "iogurte",
                "barra de cereal",
                "pudim",
                "gelatina",
            )
        )
    ):
        return "sobremesa"
    return "principal" if n == 0 else "acompanhamento"


def extrair_itens(cardapio):
    if not cardapio.strip():
        return []
    linhas = [
        x.strip()
        for x in re.split(r"(?im)^\s*observaç(?:ão|ões)\s*:\s*", cardapio, maxsplit=1)[0].splitlines()
        if x.strip()
    ]
    if linhas and _titulo(normalizar(linhas[0])):
        linhas.pop(0)
    itens = []
    contador = 0
    for linha in linhas:
        if _titulo(normalizar(linha)):
            continue
        if chave_texto(linha) in COMBINACOES_SEPARADAS:
            itens += [_item(x) for x in COMBINACOES_SEPARADAS[chave_texto(linha)]]
            continue
        ps = _split_barra(linha)
        if len(ps) > 1:
            contador += 1
            for p in ps:
                nome, rest = _variante(p)
                itens.append(_item(nome, rest, f"alternativa_{contador}"))
        else:
            nome, rest = _variante(linha)
            itens.append(_item(nome, rest))
    for n, i in enumerate(itens):
        i["papel"] = _papel(i, n)
    return itens


def _extrair_pratos(c):
    return [i["texto"] for i in extrair_itens(c)]


def _relacao_item(i, v):
    return next(
        (r["tipo"] for r in i["relacoes"] if chave_texto(r["valor"]) == chave_texto(v)),
        "componente",
    )


CARDAPIO_EXEMPLO = """Almoço Vegano de Segunda-feira

Pts com ervilha partida, chuchu e cará
Arroz integral e feijão
Batatas bravas (com páprica)
Salada de beterraba ralada
Maçã
Refresco de maracujá (RS) / refresco de pêssego (RU/RA/HC/CAISM)

Observações:
Contém glúten no pão.
"""
