"""Pipeline nutricional consolidado TACO + TBCA para cardápios do Bandeco."""

from __future__ import annotations

import csv
import gc
import hashlib
import io
import json
import logging
import re
import threading
import time
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from PIL import Image, ImageOps

MODELO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODELO_RERANKER = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
TACO_CSV_URL = "https://raw.githubusercontent.com/brolesi/taco/main/data/processed/taco/taco_composicao.csv"
TBCA_LOCAL_URL = "https://raw.githubusercontent.com/raul-rznd/web-scraping-tbca/refs/heads/main/alimentos.txt"
CACHE_DIR = Path(".cache_bandeco_nutricao")
TACO_CACHE = CACHE_DIR / "taco_composicao.csv"
TBCA_DIR = CACHE_DIR / "tbca"
TBCA_LOCAL_CACHE = TBCA_DIR / "alimentos.txt"
CATALOGO_DIR = CACHE_DIR / "catalogo"
CATALOGO_REFERENCIAS_PATH = CATALOGO_DIR / "referencias_auto_v9.json"
CACHE_TABELA_ARQUIVO = "cache_tabela_nutricional.json"
CACHE_TABELA_TTL_HOURS = 24
PIPELINE_SCHEMA_VERSION = "v14-porcoes-padronizadas"
TEMPO_OCIOSO_MODELOS_SEGUNDOS = 60
logger = logging.getLogger(__name__)
TOP_K_TACO = 10
TOP_K_TBCA = 10
TOP_K_RERANK = 15
GAP_MINIMO = 0.03
SCORE_MINIMO = 0.30
DELTA_SCORE_FAIXA = 0.10
NUTRIENTES_CHAVE = (
    "energia_kcal",
    "proteina_g",
    "carboidrato_g",
    "lipideos_g",
    "fibra_g",
    "sodio_mg",
)
COLUNAS_SOMA = [
    f"{n}_{s}"
    for n in ("kcal", "proteina_g", "carbo_g", "lipidios_g", "fibra_g", "sodio_mg")
    for s in ("min", "est", "max")
]


class DadosNutricionaisIndisponiveis(RuntimeError):
    pass


def _dirs():
    for p in (CACHE_DIR, TBCA_DIR, CATALOGO_DIR):
        p.mkdir(parents=True, exist_ok=True)


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
    _dirs()
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
    _dirs()
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


def _nome_matching(n):
    p = [x.strip() for x in re.sub(r"\[[^\]]*\]", " ", n).split(",")]
    while len(p) > 1 and re.match(r"^[A-Z][a-z]+\s+[a-z]", p[-1]):
        p.pop()
    return re.sub(r"\s+", " ", ", ".join(x for x in p if x)).strip(" ,")


BASES = {
    x: {x}
    for x in (
        "ervilha",
        "chuchu",
        "cara",
        "arroz",
        "feijao",
        "batata",
        "beterraba",
        "maca",
        "pessego",
        "maracuja",
        "paprica",
        "repolho",
        "cenoura",
        "abobrinha",
        "berinjela",
        "mandioca",
        "tomate",
        "banana",
        "milho",
        "abobora",
        "vagem",
        "lentilha",
    )
}
BASES["proteina texturizada de soja"] = {
    "proteina texturizada de soja",
    "proteina de soja texturizada",
    "soja proteina texturizada",
}
VARIEDADES_FEIJAO = {"carioca", "preto", "rajado", "roxo", "rosinha", "jalo"}
PREPAROS_PTS = {
    "refogada",
    "refogado",
    "cozida",
    "cozido",
    "preparada",
    "preparado",
    "hidratada",
    "hidratado",
}


def _base(q):
    k = chave_texto(q)
    if "proteina texturizada de soja" in k or "proteina de soja texturizada" in k:
        return "proteina texturizada de soja"
    tokens = set(k.split())
    plurais = {"batatas": "batata", "ervilhas": "ervilha", "macas": "maca"}
    for plural, singular in plurais.items():
        if plural in tokens:
            tokens.add(singular)
    return next((b for b in BASES if b in tokens), None)


def _preparado(c):
    return any(
        x in chave_texto(c["nome"])
        for x in (
            "cozido",
            "cozida",
            "refogado",
            "refogada",
            "frito",
            "frita",
            "assado",
            "assada",
            "saute",
        )
    )


def _pts(q):
    return _base(q) == "proteina texturizada de soja"


def _pts_preparada(c):
    n = chave_texto(_nome_matching(c["nome"]))
    return (
        n.startswith("soja proteina texturizada")
        or n.startswith("proteina texturizada de soja")
        or n.startswith("proteina de soja texturizada")
    ) and any(x in n for x in PREPAROS_PTS)


def candidato_compativel(q, c, contexto=None):
    k, n, b = chave_texto(q), chave_texto(_nome_matching(c["nome"])), _base(q)
    contexto = contexto or {}
    if b and not any(n == chave_texto(x) or n.startswith(chave_texto(x) + " ") for x in BASES[b]):
        return False
    if "integral" in k and "integral" not in n:
        return False
    if k == "arroz integral" and not n.startswith("arroz integral"):
        return False
    if any(x in n for x in ("mcdonald", "burger king", "fast food")):
        return False
    if (
        " com " in f" {n} "
        and " com " not in f" {k} "
        and not set(n.split(" com ", 1)[1].split()).issubset({"sal", "oleo", "agua", "casca"})
    ):
        return False
    if "ervilha" in k and "partida" in k and (not any(x in n for x in ("partida", "seca")) or "vagem" in n):
        return False
    if "ervilha" in k and "partida" in k and contexto.get("papel") == "ingrediente" and "cozid" not in n:
        return False
    if "beterraba" in k and "ralada" in k and not any(x in n for x in ("crua", "cru", "in natura", "ralada")):
        return False
    if (
        b == "batata"
        and "brava" in k
        and any(
            x in n
            for x in (
                "batata doce",
                "batata baroa",
                "mandioquinha",
                "batata salsa",
                " crua",
                " cru",
                "chips",
                "industrial",
            )
        )
    ):
        return False
    if k == "feijao" and any(x in n for x in ("tropeiro", "feijoada", "broto", "doce")):
        return False
    if b in {"arroz", "feijao"} and not _preparado(c):
        return False
    if (
        contexto.get("papel") == "ingrediente"
        and b in {"ervilha", "chuchu", "cara", "batata", "mandioca"}
        and any(x in f" {n}" for x in (" cru", " crua"))
    ):
        return False
    return True


def _familia(c):
    return re.sub(
        r"\s+",
        " ",
        re.sub(
            r"\b(?:s|c|sem|com)\s+sal\b|\bbrasil\b",
            " ",
            chave_texto(_nome_matching(c["nome"])),
        ),
    ).strip()


def calcular_gap_familias(cs):
    if len(cs) < 2:
        return None
    f = _familia(cs[0])
    return next(
        (cs[0]["score_final"] - c["score_final"] for c in cs[1:] if _familia(c) != f),
        None,
    )


def _json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _salvar_json(p, d):
    t = p.with_suffix(".tmp")
    t.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    t.replace(p)


@dataclass
class PipelineNutricional:
    base_taco: list
    base_tbca: list
    embedding_model: Any
    reranker: Any
    torch: Any
    util: Any
    device: str
    embeddings_taco: Any
    embeddings_tbca: Any
    catalogo_referencias: dict

    _modelos_lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _timer_descarga: Optional[threading.Timer] = field(default=None, init=False, repr=False)
    _usos_modelos: int = field(default=0, init=False, repr=False)

    @classmethod
    def carregar(cls):
        _dirs()
        ta, tb = carregar_taco(), carregar_tbca_local()
        p = cls(
            ta,
            tb,
            None,
            None,
            None,
            None,
            "cpu",
            None,
            None,
            _json(CATALOGO_REFERENCIAS_PATH),
        )
        with p._modelos_lock:
            p._carregar_modelos()
            p._agendar_descarga_bloqueada()
        return p

    def _carregar_modelos(self) -> None:
        if self.embedding_model is not None and self.reranker is not None:
            return

        inicio = time.perf_counter()
        logger.info("Carregando embedding e reranker na memória...")
        try:
            import torch
            from sentence_transformers import CrossEncoder, SentenceTransformer, util

            self.torch = torch
            self.util = util
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.embedding_model = SentenceTransformer(MODELO_EMBEDDING, device=self.device)
            self.reranker = CrossEncoder(
                MODELO_RERANKER,
                device=self.device,
                activation_fn=torch.nn.Sigmoid(),
            )
            self.embeddings_taco = self._emb(
                "taco",
                [normalizar(x["nome"]) for x in self.base_taco],
            )
            self.embeddings_tbca = self._emb(
                "tbca_matching_v8",
                [normalizar(_nome_matching(x["nome"])) for x in self.base_tbca],
            )
        except Exception:
            self.embedding_model = None
            self.reranker = None
            self.embeddings_taco = None
            self.embeddings_tbca = None
            raise
        logger.info(
            "Embedding e reranker carregados em %.2fs (dispositivo: %s).",
            time.perf_counter() - inicio,
            self.device,
        )

    def _descarregar_modelos_se_ocioso(self) -> None:
        with self._modelos_lock:
            self._timer_descarga = None
            if self._usos_modelos or self.embedding_model is None:
                return
            self.embedding_model = None
            self.reranker = None
            self.embeddings_taco = None
            self.embeddings_tbca = None
            if self.device == "cuda" and self.torch is not None:
                self.torch.cuda.empty_cache()
        gc.collect()
        logger.info(
            "Embedding, reranker e tensores descarregados após %ss sem uso; bases TACO/TBCA mantidas.",
            TEMPO_OCIOSO_MODELOS_SEGUNDOS,
        )

    @contextmanager
    def modelos_em_uso(self):
        with self._modelos_lock:
            self._cancelar_descarga_bloqueada()
            self._usos_modelos += 1
            try:
                self._carregar_modelos()
            except Exception:
                self._usos_modelos -= 1
                raise
        try:
            yield
        finally:
            with self._modelos_lock:
                self._usos_modelos -= 1
                if self._usos_modelos == 0:
                    self._agendar_descarga_bloqueada()

    def _agendar_descarga_bloqueada(self) -> None:
        self._cancelar_descarga_bloqueada()
        timer = threading.Timer(
            TEMPO_OCIOSO_MODELOS_SEGUNDOS,
            self._descarregar_modelos_se_ocioso,
        )
        timer.daemon = True
        self._timer_descarga = timer
        timer.start()

    def _cancelar_descarga_bloqueada(self) -> None:
        if self._timer_descarga is not None:
            self._timer_descarga.cancel()
            self._timer_descarga = None

    def _emb(self, nome, textos):
        h = hashlib.sha256((MODELO_EMBEDDING + "\n" + "\n".join(textos)).encode()).hexdigest()[:20]
        a = CACHE_DIR / f"{nome}_embeddings_{h}.pt"
        for obsoleto in CACHE_DIR.glob(f"{nome}_embeddings_*.pt"):
            if obsoleto != a:
                try:
                    obsoleto.unlink()
                except OSError:
                    logger.warning("Não foi possível remover embedding obsoleto: %s", obsoleto)
        if a.exists():
            try:
                return self.torch.load(a, map_location="cpu", weights_only=True).to(self.device)
            except TypeError:
                return self.torch.load(a, map_location="cpu").to(self.device)
        e = self.embedding_model.encode(
            textos,
            normalize_embeddings=True,
            convert_to_tensor=True,
            show_progress_bar=False,
        )
        temporario = a.with_suffix(".tmp")
        self.torch.save(e.detach().cpu(), temporario)
        temporario.replace(a)
        return e

    def _rec(self, q, base, emb, k, ctx, tb=False):
        ids = [
            i for i, c in enumerate(base) if (_pts_preparada(c) if tb and _pts(q) else candidato_compativel(q, c, ctx))
        ]
        if not ids:
            return []
        qe = self.embedding_model.encode(normalizar(q), normalize_embeddings=True, convert_to_tensor=True)
        sc = self.util.dot_score(qe, emb[ids])[0]
        top = self.torch.topk(sc, k=min(k, len(ids)))
        return [
            {**base[ids[j.item()]], "score_embedding": float(s)} for s, j in zip(top.values, top.indices, strict=True)
        ]

    def reranquear(self, q, cs):
        cs = sorted(cs, key=lambda x: x["score_embedding"], reverse=True)[:TOP_K_RERANK]
        if not cs:
            return []
        sc = self.reranker.predict([(normalizar(q), normalizar(_nome_matching(c["nome"]))) for c in cs])
        return sorted(
            [{**c, "score_reranker": float(s), "score_final": float(s)} for c, s in zip(cs, sc, strict=True)],
            key=lambda x: x["score_final"],
            reverse=True,
        )

    def _memorizar(self, chave, resultado):
        self.catalogo_referencias[chave] = resultado
        _salvar_json(CATALOGO_REFERENCIAS_PATH, self.catalogo_referencias)
        return resultado

    def buscar_referencia(self, q, ctx=None):
        ctx = ctx or {}
        chave = hashlib.sha256(
            json.dumps(
                [
                    PIPELINE_SCHEMA_VERSION,
                    MODELO_EMBEDDING,
                    MODELO_RERANKER,
                    chave_texto(q),
                    ctx,
                ],
                sort_keys=True,
                ensure_ascii=False,
            ).encode()
        ).hexdigest()
        if chave_texto(q) in GENERICOS_EXATOS:
            return _sem(q, "categoria_generica")
        if chave in self.catalogo_referencias:
            return self.catalogo_referencias[chave]
        with self.modelos_em_uso():
            return self._buscar_referencia_com_modelos(q, ctx, chave)

    def _buscar_referencia_com_modelos(self, q, ctx, chave):
        if "refresco" in chave_texto(q):
            fruta = next(
                (
                    f
                    for f in (
                        "pessego",
                        "maracuja",
                        "uva",
                        "laranja",
                        "manga",
                        "goiaba",
                        "abacaxi",
                        "caju",
                        "acerola",
                        "limao",
                        "morango",
                        "framboesa",
                    )
                    if f in chave_texto(q)
                ),
                None,
            )
            cs = [
                c
                for c in self.base_taco + self.base_tbca
                if fruta
                and fruta in chave_texto(c["nome"])
                and any(x in chave_texto(c["nome"]) for x in ("refresco", "nectar", "suco"))
                and not any(x in chave_texto(c["nome"]) for x in ("leite", "iogurte", "soja extrato"))
            ]
            if cs:
                textos = [normalizar(_nome_matching(c["nome"])) for c in cs]
                e = self.embedding_model.encode(textos, normalize_embeddings=True, convert_to_tensor=True)
                qe = self.embedding_model.encode(normalizar(q), normalize_embeddings=True, convert_to_tensor=True)
                scores = self.util.dot_score(qe, e)[0]
                rr = self.reranquear(q, [{**c, "score_embedding": float(s)} for c, s in zip(cs, scores, strict=True)])
                m = rr[0]
                return self._memorizar(
                    chave,
                    {
                        "query": q,
                        "query_resolvida": m["nome"],
                        "status": "proxy_controlado",
                        "gap": calcular_gap_familias(rr),
                        "resultado": m,
                        "candidatos_taco": [],
                        "candidatos_tbca": [],
                        "candidatos_reranker": rr,
                    },
                )
        ta = [] if _pts(q) else self._rec(q, self.base_taco, self.embeddings_taco, TOP_K_TACO, ctx)
        tb = self._rec(q, self.base_tbca, self.embeddings_tbca, TOP_K_TBCA, ctx, True)
        rr = self.reranquear(q, ta + tb)
        if not rr:
            return _sem(q, "sem_referencia_preparada" if _pts(q) else "sem_match", ta, tb)
        m, g = rr[0], calcular_gap_familias(rr)
        status = (
            "aceito"
            if m["score_final"] >= SCORE_MINIMO and (g is None or g >= GAP_MINIMO)
            else "baixa_confianca"
            if m["score_final"] < SCORE_MINIMO
            else "ambiguo"
        )
        if chave_texto(q) == "feijao":
            status = "variedade_desconhecida"
        if "beterraba" in chave_texto(q) and "ralada" in chave_texto(q):
            status = "aceito"
        return self._memorizar(
            chave,
            {
                "query": q,
                "status": status,
                "gap": g,
                "resultado": m,
                "candidatos_taco": ta,
                "candidatos_tbca": tb,
                "candidatos_reranker": rr,
            },
        )


def _sem(q, s, ta=(), tb=()):
    return {
        "query": q,
        "status": s,
        "gap": None,
        "resultado": None,
        "candidatos_taco": list(ta),
        "candidatos_tbca": list(tb),
        "candidatos_reranker": [],
    }


_PIPELINE = None
_LOCK = threading.Lock()


def obter_pipeline():
    global _PIPELINE
    if _PIPELINE is None:
        with _LOCK:
            if _PIPELINE is None:
                _PIPELINE = PipelineNutricional.carregar()
    return _PIPELINE


def inicializar_pipeline_nutricional() -> PipelineNutricional:
    return obter_pipeline()


def buscar_referencia(q, contexto=None):
    return obter_pipeline().buscar_referencia(q, contexto)


def _marcador(t):
    q = chave_texto(t)
    return next((x for x in PREPARACOES_NOMEADAS if x in q), None)


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


def _gerar_imagem_tabela(dados):
    fig, ax = plt.subplots(figsize=(14, max(4, 0.45 * len(dados))))
    t = ax.table(cellText=dados, loc="center", cellLoc="center")
    t.auto_set_font_size(False)
    t.set_fontsize(8)
    t.auto_set_column_width(col=list(range(8)))
    ax.axis("off")
    a = "tabela_temporaria.jpg"
    plt.savefig(a, bbox_inches="tight", pad_inches=0.05, dpi=160)
    plt.close(fig)
    with Image.open(a) as im:
        im.load()
        box = ImageOps.invert(im.convert("RGB")).getbbox()
        if box:
            im.crop(tuple(np.asarray(box))).save(a)
    return a[:-4]


def gerar_tabela_nutricional(cardapio) -> Optional[str]:
    if not extrair_itens(cardapio):
        return None
    h = _hash_cardapio(cardapio)
    cache = _carregar_cache_tabela(h)
    if cache is not None:
        return _gerar_imagem_tabela(cache)
    try:
        r = processar_cardapio(cardapio)
    except DadosNutricionaisIndisponiveis:
        return None
    d = _projetar_formato_antigo(r)
    _salvar_cache_tabela(d, h)
    return _gerar_imagem_tabela(d)


def imprimir_match(titulo, r):
    print(f"\n>>> {titulo}: {r['query']}\n  Status: {r['status']}")
    m = r.get("resultado")
    if m:
        print(
            f"  [{m['fonte']}] {m['nome']} | emb={m.get('score_embedding', 0):.4f} | CE/final={m.get('score_final', 0):.4f}"
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


def main():
    r = processar_cardapio(CARDAPIO_EXEMPLO)
    print("\nTABELA FINAL — COMPONENTES")
    print(r.componentes.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("\nTABELA FINAL — TOTAIS")
    print(r.totais.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    r.componentes.to_csv("tabela_nutricional_componentes.csv", index=False, encoding="utf-8-sig")
    r.totais.to_csv("tabela_nutricional_totais.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
