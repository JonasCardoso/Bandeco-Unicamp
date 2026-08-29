"""Repositório Firebase inicializado explicitamente, sem efeitos colaterais no import."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import credentials, db

from settings import Settings

logger = logging.getLogger(__name__)


def _ler_json(caminho: Path) -> dict[str, Any] | None:
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return dados if isinstance(dados, dict) else None


def _get_firebase_credentials_dict() -> dict[str, Any]:
    """Carrega credenciais de FIREBASE_JSON (JSON ou path) ou firebase.json."""
    valor = Settings().firebase_json
    if valor and valor.strip():
        try:
            dados = json.loads(valor)
        except json.JSONDecodeError:
            dados = _ler_json(Path(valor))
        if isinstance(dados, dict):
            return dados

    dados = _ler_json(Path("firebase.json"))
    if dados is not None:
        return dados
    raise ValueError(
        "Credenciais do Firebase não encontradas ou inválidas. "
        "Defina FIREBASE_JSON com JSON/caminho válido ou crie firebase.json."
    )


def inicializar_firebase() -> None:
    """Inicializa o SDK uma única vez, no estágio explícito de startup."""
    if firebase_admin._apps:
        return
    config = Settings()
    if not config.database_url_firebase:
        raise ValueError("DATABASE_URL_FIREBASE não definida")
    credencial = credentials.Certificate(_get_firebase_credentials_dict())
    firebase_admin.initialize_app(credencial, {"databaseURL": config.database_url_firebase})


class Config:
    """Compatibilidade: repositório de usuários persistidos no Firebase."""

    def __init__(self, ref=None):
        if ref is None:
            inicializar_firebase()
            ref = db.reference("/usuarios")
        self.ref = ref

    def adicionar_contato(self, dados: dict[str, object], id_user: str) -> bool:
        try:
            self.ref.child(str(id_user)).update(dados)
            return True
        except firebase_admin.exceptions.FirebaseError:
            logger.exception("Falha ao adicionar contato do usuário %s", id_user)
            return False

    def atualizar_usuario(self, dados: dict[str, object], id_user: str) -> bool:
        try:
            self.ref.child(str(id_user)).update(dados)
            return True
        except firebase_admin.exceptions.FirebaseError:
            logger.exception("Falha ao atualizar usuário %s", id_user)
            return False

    def pegar_todos_usuarios(self) -> dict[str, object] | bool:
        try:
            item = self.ref.get()
            return dict(item) if item else False
        except (firebase_admin.exceptions.FirebaseError, TypeError, ValueError):
            logger.exception("Falha ao recuperar usuários")
            return False

    def pegar_usuario(self, id_user: str) -> dict[str, object] | bool:
        try:
            item = self.ref.order_by_key().equal_to(str(id_user)).get()
            dados = dict(item) if item else {}
            return dados.get(str(id_user), False)
        except (firebase_admin.exceptions.FirebaseError, TypeError, ValueError):
            logger.exception("Falha ao recuperar usuário %s", id_user)
            return False

    def criar_usuario(self, id_user: str) -> bool:
        dados = {"tradicional": 1, "vegano": 0, "cafe": 0, "almoco": 1, "jantar": 1, "telefone": 0}
        return self.atualizar_usuario(dados, str(id_user))


@lru_cache(maxsize=1)
def get_firebase() -> Config:
    """Retorna o repositório compartilhado, criado apenas no primeiro uso."""
    return Config()


def clear_firebase_cache() -> None:
    get_firebase.cache_clear()
