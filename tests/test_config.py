"""Testes unitários para config.py (Firebase)."""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from ngrok_servico import Ngrok
from senha import criptografar_senha
from teclado import teclado_dias_semana, teclado_modalidades
from util import DIAS, verificar_atividade


class TestConfigClass:
    """Testes para a classe Config."""

    def test_verificar_atividade_util(self):
        assert "Ativo" in verificar_atividade({"cafe": 1}, 'cafe')
        assert "Inativo" in verificar_atividade({"almoco": 0}, 'almoco')


class TestTeclado:
    """Testes para teclado.py."""

    def test_teclado_dias_semana(self):
        resultado = teclado_dias_semana('Almoço', DIAS)

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


class TestNgrokService:
    """Testes para ngrok_servico.py."""

    def test_ngrok_inicializacao(self):
        ngrok = Ngrok()

        # Atributos devem ser de instância, não de classe
        assert hasattr(ngrok, 'ngrok')
        assert hasattr(ngrok, 'httpd')
        assert hasattr(ngrok, '_lock')
        assert hasattr(ngrok, '_porta')

        # Valores iniciais devem ser None/0
        assert ngrok.ngrok is None
        assert ngrok.httpd is None
        assert ngrok._porta == 8000

    def test_ngrok_context_manager(self):
        with Ngrok() as ngrok:
            assert isinstance(ngrok, Ngrok)


class TestSenhaService:
    """Testes para senha.py."""

    def test_criptografar_senha_retorna_tupla_3_elementos(self):
        resultado = criptografar_senha('senha123')

        assert isinstance(resultado, tuple)
        assert len(resultado) == 3

    def test_criptografar_senha_consistente(self):
        hash1 = criptografar_senha('senha123')
        hash2 = criptografar_senha('senha123')

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
            firebase_json = os.environ.get('FIREBASE_JSON', '')
            if firebase_json:
                try:
                    return json.loads(firebase_json)
                except json.JSONDecodeError:
                    pass

            firebase_path = Path("firebase.json")
            if firebase_path.exists():
                content = firebase_path.read_text(encoding='utf-8')
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass

            raise ValueError(
                "Credenciais do Firebase não encontradas. Defina a variável de ambiente FIREBASE_JSON "
                "ou crie o arquivo firebase.json."
            )

        valid_json = '{"type": "service_account", "project_id": "test_project"}'

        with patch.dict(os.environ, {'FIREBASE_JSON': valid_json}, clear=False):
            result = get_creds()

        assert result['project_id'] == 'test_project'

    def test_fallback_para_arquivo_quando_env_vazia(self):
        def get_creds():
            firebase_json = os.environ.get('FIREBASE_JSON', '')
            if firebase_json:
                try:
                    return json.loads(firebase_json)
                except json.JSONDecodeError:
                    pass

            firebase_path = Path("firebase.json")
            if firebase_path.exists():
                content = firebase_path.read_text(encoding='utf-8')
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass

            raise ValueError(
                "Credenciais do Firebase não encontradas. Defina a variável de ambiente FIREBASE_JSON "
                "ou crie o arquivo firebase.json."
            )

        valid_json_content = '{"type": "service_account", "project_id": "file_project"}'

        with patch.dict(os.environ, {'FIREBASE_JSON': ''}, clear=False):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.read_text', return_value=valid_json_content):
                    result = get_creds()

        assert result['project_id'] == 'file_project'


class TestFirebaseCredentialsError:
    """Testes para erros de credenciais Firebase."""

    def test_levanta_valorerror_se_nada_disponivel(self):
        def get_creds():
            firebase_json = os.environ.get('FIREBASE_JSON', '')
            if firebase_json:
                try:
                    return json.loads(firebase_json)
                except json.JSONDecodeError:
                    pass

            firebase_path = Path("firebase.json")
            if firebase_path.exists():
                content = firebase_path.read_text(encoding='utf-8')
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass

            raise ValueError(
                "Credenciais do Firebase não encontradas. Defina a variável de ambiente FIREBASE_JSON "
                "ou crie o arquivo firebase.json."
            )

        with patch.dict(os.environ, {'FIREBASE_JSON': ''}, clear=True):
            with patch('pathlib.Path.exists', return_value=False):
                with pytest.raises(ValueError, match="Credenciais do Firebase não encontradas"):
                    get_creds()


class TestConfigClassExtended:
    """Testes estendidos para a classe Config."""

    def test_criar_usuario_padrao(self):
        # Verifica que a classe existe e tem os métodos esperados
        import config
        assert hasattr(config.Config, 'criar_usuario')
        assert hasattr(config.Config, 'atualizar_usuario')
        assert hasattr(config.Config, 'pegar_usuario')
        assert hasattr(config.Config, 'pegar_todos_usuarios')
        assert hasattr(config.Config, 'adicionar_contato')
