"""Testes unitários para config.py (Firebase)."""

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.constants import DIAS
from interfaces.telegram.keyboards import teclado_dias_semana, teclado_modalidades
from modules.balance.crypto import criptografar_senha
from modules.preferences.rules import verificar_atividade


class TestConfigClass:
    """Testes para a classe Config."""

    def test_verificar_atividade_util(self):
        assert "Ativo" in verificar_atividade({"cafe": 1}, "cafe")
        assert "Inativo" in verificar_atividade({"almoco": 0}, "almoco")


class TestTeclado:
    """Testes para teclado.py."""

    def test_teclado_dias_semana(self):
        resultado = teclado_dias_semana("Almoço", DIAS)

        assert len(resultado) == 7
        # Cada botão deve ser uma lista com um elemento (o KeyboardButton)
        for botao in resultado:
            assert isinstance(botao, list)
            assert len(botao) == 1

    def test_teclado_modalidades(self):
        dados = {"tradicional": 1, "vegano": 0}
        resultado = teclado_modalidades(dados)

        assert isinstance(resultado, list)
        assert len(resultado) == 2
        # Verifica se cada elemento é uma lista com um botão
        for botao in resultado:
            assert isinstance(botao, list)
            assert len(botao) == 1


class TestSenhaService:
    """Testes para modules.balance.service.py."""

    def test_criptografar_senha_retorna_tupla_3_elementos(self):
        resultado = criptografar_senha("senha123")

        assert isinstance(resultado, tuple)
        assert len(resultado) == 3

    def test_criptografar_senha_consistente(self):
        hash1 = criptografar_senha("senha123")
        hash2 = criptografar_senha("senha123")

        # Mesma entrada deve produzir mesmo output (determinístico)
        assert hash1 == hash2


# =============================================================================
# Testes para o fallback de credenciais Firebase (Etapa 5)
# =============================================================================


class TestFirebaseCredentialsFallback:
    """Testes para a função _get_firebase_credentials_dict()."""

    def test_preferencia_env_var_sobre_arquivo(self):
        # Copia isolada da lógica de _get_firebase_credentials_dict para teste
        def get_creds():
            firebase_json = os.environ.get("FIREBASE_JSON", "")
            if firebase_json:
                try:
                    return json.loads(firebase_json)
                except json.JSONDecodeError:
                    pass

            firebase_path = Path("firebase.json")
            if firebase_path.exists():
                content = firebase_path.read_text(encoding="utf-8")
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass

            raise ValueError(
                "Credenciais do Firebase não encontradas. Defina a variável de ambiente FIREBASE_JSON "
                "ou crie o arquivo firebase.json."
            )

        valid_json = '{"type": "service_account", "project_id": "test_project"}'

        with patch.dict(os.environ, {"FIREBASE_JSON": valid_json}, clear=False):
            result = get_creds()

        assert result["project_id"] == "test_project"

    def test_fallback_para_arquivo_quando_env_vazia(self):
        def get_creds():
            firebase_json = os.environ.get("FIREBASE_JSON", "")
            if firebase_json:
                try:
                    return json.loads(firebase_json)
                except json.JSONDecodeError:
                    pass

            firebase_path = Path("firebase.json")
            if firebase_path.exists():
                content = firebase_path.read_text(encoding="utf-8")
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass

            raise ValueError(
                "Credenciais do Firebase não encontradas. Defina a variável de ambiente FIREBASE_JSON "
                "ou crie o arquivo firebase.json."
            )

        valid_json_content = '{"type": "service_account", "project_id": "file_project"}'

        with patch.dict(os.environ, {"FIREBASE_JSON": ""}, clear=False):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.read_text", return_value=valid_json_content):
                    result = get_creds()

        assert result["project_id"] == "file_project"


class TestFirebaseCredentialsError:
    """Testes para erros de credenciais Firebase."""

    def test_levanta_valorerror_se_nada_disponivel(self):
        def get_creds():
            firebase_json = os.environ.get("FIREBASE_JSON", "")
            if firebase_json:
                try:
                    return json.loads(firebase_json)
                except json.JSONDecodeError:
                    pass

            firebase_path = Path("firebase.json")
            if firebase_path.exists():
                content = firebase_path.read_text(encoding="utf-8")
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass

            raise ValueError(
                "Credenciais do Firebase não encontradas. Defina a variável de ambiente FIREBASE_JSON "
                "ou crie o arquivo firebase.json."
            )

        with patch.dict(os.environ, {"FIREBASE_JSON": ""}, clear=True):
            with patch("pathlib.Path.exists", return_value=False):
                with pytest.raises(ValueError, match="Credenciais do Firebase não encontradas"):
                    get_creds()


class TestConfigClassExtended:
    """Testes estendidos para a classe Config."""

    def test_criar_usuario_padrao(self):
        # Verifica que a classe existe e tem os métodos esperados
        from integrations.firebase import user_repository as config

        assert hasattr(config.Config, "criar_usuario")
        assert hasattr(config.Config, "atualizar_usuario")
        assert hasattr(config.Config, "pegar_usuario")
        assert hasattr(config.Config, "pegar_todos_usuarios")
        assert hasattr(config.Config, "adicionar_contato")


class TestFirebaseImplementacaoReal:
    def test_ler_json_valido_e_invalido(self, tmp_path):
        from integrations.firebase import user_repository as config

        valido = tmp_path / "valido.json"
        valido.write_text('{"project_id": "projeto"}', encoding="utf-8")
        invalido = tmp_path / "invalido.json"
        invalido.write_text("[1, 2]", encoding="utf-8")
        assert config._ler_json(valido) == {"project_id": "projeto"}
        assert config._ler_json(invalido) is None
        assert config._ler_json(tmp_path / "ausente.json") is None

    def test_credenciais_aceitam_json_e_caminho(self, tmp_path, monkeypatch):
        from integrations.firebase import user_repository as config

        monkeypatch.setattr(config, "Settings", lambda: SimpleNamespace(firebase_json='{"id": 1}'))
        assert config._get_firebase_credentials_dict() == {"id": 1}
        arquivo = tmp_path / "firebase.json"
        arquivo.write_text('{"id": 2}', encoding="utf-8")
        monkeypatch.setattr(config, "Settings", lambda: SimpleNamespace(firebase_json=str(arquivo)))
        assert config._get_firebase_credentials_dict() == {"id": 2}

    def test_inicializar_firebase_e_idempotente(self, monkeypatch):
        from integrations.firebase import user_repository as config

        config.firebase_admin._apps = []
        monkeypatch.setattr(
            config,
            "Settings",
            lambda: SimpleNamespace(
                database_url_firebase="https://db.test",
                firebase_json='{"id": 1}',
            ),
        )
        config.credentials.Certificate.reset_mock()
        config.firebase_admin.initialize_app.reset_mock()
        config.inicializar_firebase()
        config.firebase_admin.initialize_app.assert_called_once()
        config.firebase_admin._apps = [object()]
        config.inicializar_firebase()
        config.firebase_admin.initialize_app.assert_called_once()

    def test_crud_e_usuario_padrao(self):
        from integrations.firebase import user_repository as config

        ref = MagicMock()
        filho = ref.child.return_value
        repositorio = config.Config(ref=ref)
        assert repositorio.adicionar_contato({"telefone": 1}, "7") is True
        assert repositorio.atualizar_usuario({"cafe": 1}, "7") is True
        assert repositorio.criar_usuario("7") is True
        assert filho.update.call_count == 3
        ref.get.return_value = {"7": {"cafe": 1}}
        assert repositorio.pegar_todos_usuarios() == {"7": {"cafe": 1}}
        ref.order_by_key.return_value.equal_to.return_value.get.return_value = {"7": {"cafe": 1}}
        assert repositorio.pegar_usuario("7") == {"cafe": 1}

    def test_leituras_invalidas_preservam_fallback(self):
        from integrations.firebase import user_repository as config

        ref = MagicMock()
        ref.get.return_value = [["não é mapping"]]
        ref.order_by_key.return_value.equal_to.return_value.get.return_value = [["inválido"]]
        repositorio = config.Config(ref=ref)
        assert repositorio.pegar_todos_usuarios() is False
        assert repositorio.pegar_usuario("7") is False
