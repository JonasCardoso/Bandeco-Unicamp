"""Matching semântico, modelos e ciclo de vida do pipeline."""

from __future__ import annotations

import ctypes
import gc
import hashlib
import json
import logging
import re
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Optional

from .cache import CACHE_DIR, CATALOGO_REFERENCIAS_PATH, validar_cache_gravavel
from .parser import GENERICOS_EXATOS, PREPARACOES_NOMEADAS, chave_texto, normalizar
from .sources import carregar_taco, carregar_tbca_local

MODELO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODELO_RERANKER = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
PIPELINE_SCHEMA_VERSION = "v14-porcoes-padronizadas"
TEMPO_OCIOSO_MODELOS_SEGUNDOS = 300
TOP_K_TACO = 10
TOP_K_TBCA = 10
TOP_K_RERANK = 15
GAP_MINIMO = 0.03
SCORE_MINIMO = 0.30
DELTA_SCORE_FAIXA = 0.10
logger = logging.getLogger(__name__)


def _obter_rss_mb() -> Optional[float]:
    """Retorna o RSS atual do processo em MB no Linux."""
    if not sys.platform.startswith("linux"):
        return None

    try:
        with open("/proc/self/status", encoding="utf-8") as arquivo:
            for linha in arquivo:
                if linha.startswith("VmRSS:"):
                    partes = linha.split()
                    if len(partes) < 2:
                        return None
                    return int(partes[1]) / 1024
    except (OSError, ValueError, IndexError):
        logger.debug("Não foi possível obter o RSS do processo.", exc_info=True)

    return None


def _liberar_heap_linux() -> bool:
    """Pede ao glibc que devolva páginas livres do heap ao Linux."""
    if not sys.platform.startswith("linux"):
        return False

    try:
        libc = ctypes.CDLL("libc.so.6")
        malloc_trim = libc.malloc_trim
        malloc_trim.argtypes = [ctypes.c_size_t]
        malloc_trim.restype = ctypes.c_int
        return bool(malloc_trim(0))
    except (OSError, AttributeError):
        logger.debug("malloc_trim não está disponível neste sistema.", exc_info=True)
        return False


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
        validar_cache_gravavel()
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
        """Descarrega modelos/tensores ociosos e tenta devolver RAM ao SO."""
        with self._modelos_lock:
            self._timer_descarga = None

            if self._usos_modelos:
                logger.debug(
                    "Descarga adiada: %d uso(s) ativo(s) dos modelos.",
                    self._usos_modelos,
                )
                return

            if self.embedding_model is None:
                logger.debug("Descarga ignorada: modelos já estão descarregados.")
                return

            ram_antes = _obter_rss_mb()
            torch_module = self.torch
            usar_cuda = self.device == "cuda" and torch_module is not None

            # Remove todas as referências pesadas mantidas pelo pipeline.
            self.embedding_model = None
            self.reranker = None
            self.embeddings_taco = None
            self.embeddings_tbca = None

            # Coleta ciclos/referências Python após remover os modelos.
            objetos_coletados = gc.collect()

            if usar_cuda:
                try:
                    torch_module.cuda.empty_cache()
                    if hasattr(torch_module.cuda, "ipc_collect"):
                        torch_module.cuda.ipc_collect()
                except RuntimeError:
                    logger.exception("Falha ao liberar o cache CUDA durante a descarga dos modelos.")

            # torch/util são reimportados normalmente em _carregar_modelos().
            self.torch = None
            self.util = None

            objetos_coletados += gc.collect()
            heap_reduzido = _liberar_heap_linux()
            ram_depois = _obter_rss_mb()

        if ram_antes is not None and ram_depois is not None:
            liberados = ram_antes - ram_depois
            logger.info(
                "Embedding, reranker e tensores descarregados após %ss sem uso; "
                "RAM: %.1f MB -> %.1f MB; liberados %.1f MB; GC=%d; "
                "malloc_trim=%s; bases TACO/TBCA mantidas.",
                TEMPO_OCIOSO_MODELOS_SEGUNDOS,
                ram_antes,
                ram_depois,
                liberados,
                objetos_coletados,
                heap_reduzido,
            )
        else:
            logger.info(
                "Embedding, reranker e tensores descarregados após %ss sem uso; "
                "GC=%d; malloc_trim=%s; bases TACO/TBCA mantidas.",
                TEMPO_OCIOSO_MODELOS_SEGUNDOS,
                objetos_coletados,
                heap_reduzido,
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
