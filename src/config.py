"""Configuração do Firebase para persistência de dados dos usuários.

Este módulo inicializa a conexão com o Firebase Database e fornece
uma classe Config para operações CRUD nos registros de usuários.
"""

import json
import os
import pathlib
from typing import Dict

import firebase_admin
from firebase_admin import credentials, db

from util import get_database_url_firebase


def _get_firebase_credentials_dict() -> dict:
    """Retorna as credenciais do Firebase como dicionário.

    Tenta primeiro a variável de ambiente FIREBASE_JSON (formato JSON string).
    Se não existir, tenta ler o arquivo firebase.json do disco.

    Returns:
        Dicionário com as credenciais do Firebase.

    Raises:
        ValueError: Se nem a env var nem o arquivo estiverem disponíveis.
    """
    # Tenta primeiro a variável de ambiente FIREBASE_JSON
    firebase_json_env = os.environ.get('FIREBASE_JSON')
    if firebase_json_env and firebase_json_env.strip() != '':
        try:
            return json.loads(firebase_json_env)
        except json.JSONDecodeError:
            pass  # Se falhar, tenta o arquivo

    # Fallback: tenta ler do arquivo firebase.json no disco
    firebase_path = pathlib.Path('firebase.json')
    if firebase_path.exists():
        try:
            with open(firebase_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass  # Se falhar, levanta erro

    raise ValueError(
        "Credenciais do Firebase não encontradas. "
        "Defina a variável de ambiente FIREBASE_JSON ou crie o arquivo firebase.json."
    )


# Inicializa a conexão com o Firebase apenas se ainda não foi inicializada
if not firebase_admin._apps:
    cred_dict = _get_firebase_credentials_dict()
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred, {
        'databaseURL': get_database_url_firebase()
    })



class Config:
    """Interface para operações no Firebase Database.

    Attributes:
        ref: Referência ao nó raiz '/usuarios' do banco de dados.
    """

    ref = db.reference("/usuarios")

    def adicionar_contato(self, dados: Dict[str, object], id_user: str) -> bool:
        """Adiciona ou atualiza os dados de um usuário.

        Args:
            dados: Dicionário com os dados a serem salvos.
            id_user: ID do usuário no Telegram.

        Returns:
            True se bem-sucedido, False caso contrário.
        """
        try:
            self.ref.child(str(id_user)).update(dados)
            return True
        except firebase_admin.exceptions.FirebaseError as e:
            print(f"[ERROR] Firebase - adicionar_contato({id_user}): {e}")
            return False

    def atualizar_usuario(self, dados: Dict[str, object], id_user: str) -> bool:
        """Atualiza os dados de um usuário existente.

        Args:
            dados: Dicionário com os novos dados.
            id_user: ID do usuário no Telegram.

        Returns:
            True se bem-sucedido, False caso contrário.
        """
        try:
            self.ref.child(str(id_user)).update(dados)
            return True
        except firebase_admin.exceptions.FirebaseError as e:
            print(f"[ERROR] Firebase - atualizar_usuario({id_user}): {e}")
            return False

    def pegar_todos_usuarios(self) -> Dict[str, object] | None:
        """Recupera todos os usuários cadastrados.

        Returns:
            Dicionário com todos os usuários ou None em caso de erro.
        """
        try:
            item = dict(self.ref.get())
            if len(item) > 0:
                return item
            else:
                return False
        except firebase_admin.exceptions.FirebaseError as e:
            print(f"[ERROR] Firebase - pegar_todos_usuarios(): {e}")
            return False

    def pegar_usuario(self, id_user: str) -> Dict[str, object] | None:
        """Recupera os dados de um usuário específico.

        Args:
            id_user: ID do usuário no Telegram.

        Returns:
            Dicionário com os dados do usuário ou None em caso de erro.
        """
        try:
            item = dict(self.ref.order_by_key().equal_to(str(id_user)).get())
            if len(item) > 0:
                return item[str(id_user)]
            else:
                return False
        except firebase_admin.exceptions.FirebaseError as e:
            print(f"[ERROR] Firebase - pegar_usuario({id_user}): {e}")
            return False

    def criar_usuario(self, id_user: str) -> bool:
        """Cria um novo usuário com valores padrão.

        Args:
            id_user: ID do usuário no Telegram.

        Returns:
            True se bem-sucedido, False caso contrário.
        """
        try:
            dados = {"tradicional": 1, "vegano": 0, "cafe": 0, "almoco": 1, "jantar": 1, "telefone": 0}
            return self.atualizar_usuario(dados, str(id_user))
        except firebase_admin.exceptions.FirebaseError as e:
            print(f"[ERROR] Firebase - criar_usuario({id_user}): {e}")
            return False
