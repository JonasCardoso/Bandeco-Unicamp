"""Testes unitários para utilitários (util.py)."""

import logging
from unittest.mock import patch

import pytest
import requests

from settings import REQUIRED_ENV_VARS
from util import (
    DIAS,
    MODALIDADES,
    _get_env,
    _require_env,
    log_env_validation,
    retry,
    validar_env_vars,
    verificar_atividade,
)


class TestVerificarAtividade:
    """Testes para a função verificar_atividade()."""

    def test_retorna_ativo_quando_verdadeiro(self):
        dados = {"cafe": 1}
        assert "Ativo" in verificar_atividade(dados, "cafe")

    def test_retorna_inativo_quando_falso(self):
        dados = {"almoco": 0}
        assert "Inativo" in verificar_atividade(dados, "almoco")


class TestRetryDecorator:
    """Testes para o decorator retry()."""

    def test_retry_sucesso_na_primeira_tentativa(self):
        """Se a função succeeds na primeira tentativa, retorna normalmente."""
        call_count = 0

        @retry(max_attempts=3, delay=0.1)
        def funcao_simples():
            nonlocal call_count
            call_count += 1
            return "sucesso"

        result = funcao_simples()
        assert result == "sucesso"
        assert call_count == 1

    def test_retry_sucesso_na_segunda_tentativa(self):
        """Se a função falha na primeira e succeeds na segunda, retry funciona."""
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def funcao_intermitente():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Erro temporário")
            return "sucesso"

        result = funcao_intermitente()
        assert result == "sucesso"
        assert call_count == 2

    def test_retry_esgota_todas_as_tentativas(self):
        """Se a função sempre falha, levanta exceção após todas as tentativas."""

        @retry(max_attempts=3, delay=0.01)
        def funcao_sempre_falha():
            raise ValueError("Erro permanente")

        with pytest.raises(ValueError, match="Erro permanente"):
            funcao_sempre_falha()

    @pytest.mark.asyncio
    async def test_retry_assincrono(self, monkeypatch):
        chamadas = 0

        async def sem_espera(_):
            return None

        monkeypatch.setattr("util.asyncio.sleep", sem_espera)

        @retry(max_attempts=2, delay=0.01, exceptions=(ValueError,))
        async def instavel():
            nonlocal chamadas
            chamadas += 1
            if chamadas == 1:
                raise ValueError("temporário")
            return "ok"

        assert await instavel() == "ok"
        assert chamadas == 2

    def test_retry_nao_repete_em_erro_diferente(self):
        """Retry só repete para as exceções especificadas."""
        call_count = 0

        @retry(max_attempts=3, delay=0.01, exceptions=requests.RequestException)
        def funcao_com_erro_nao_retriable():
            nonlocal call_count
            call_count += 1
            raise ValueError("Erro não retrátil")

        # Deve levantar imediatamente sem retry
        with pytest.raises(ValueError):
            funcao_com_erro_nao_retriable()
        assert call_count == 1


class TestRequireEnv:
    """Testes para validação de variáveis de ambiente."""

    def test_require_env_variavel_existente(self):
        with patch.dict("os.environ", {"TEST_VAR_EXISTENTE": "valor_teste"}):
            result = _require_env("TEST_VAR_EXISTENTE")
            assert result == "valor_teste"

    def test_require_env_variavel_inexistente(self):
        # Garante que a variável não existe
        env_copy = dict(__import__("os").environ)
        if "TEST_VAR_INEXISTENTE" in env_copy:
            del env_copy["TEST_VAR_INEXISTENTE"]
        with patch.dict("os.environ", env_copy, clear=False):
            original = __import__("os").environ.pop("TEST_VAR_INEXISTENTE", None)
            try:
                with pytest.raises(ValueError, match="Variável de ambiente obrigatória"):
                    _require_env("TEST_VAR_INEXISTENTE")
            finally:
                if original is not None:
                    __import__("os").environ["TEST_VAR_INEXISTENTE"] = original

    def test_get_env_retorna_none(self):
        assert _get_env("VARIAVEL_INEXISTENTE_TESTE_999") is None

    def test_get_env_respeita_default(self):
        assert _get_env("VARIAVEL_INEXISTENTE_TESTE_999", "padrao") == "padrao"


class TestConstants:
    """Testes para constantes do módulo util."""

    def test_dias_contem_segunda_a_domingo(self):
        assert len(DIAS) == 7
        assert DIAS[0] == "Segunda-feira"
        assert DIAS[-1] == "Domingo"

    def test_modalidades_contem_tipos_esperados(self):
        assert len(MODALIDADES) == 5
        assert "Almoço Tradicional" in MODALIDADES
        assert "Almoço Vegano" in MODALIDADES
        assert "Café da manhã" in MODALIDADES


# =============================================================================
# Testes para validar_env_vars e log_env_validation
# =============================================================================


class TestValidarEnvVars:
    """Testes para a fonte única de variáveis obrigatórias."""

    def test_retorna_lista_vazia_quando_todas_presentes(self, monkeypatch):
        for var in REQUIRED_ENV_VARS:
            monkeypatch.setenv(var, "valor")
        assert validar_env_vars() == []

    def test_retorna_variaveis_faltando(self, monkeypatch):
        for var in REQUIRED_ENV_VARS:
            monkeypatch.setenv(var, "")
        monkeypatch.setenv("TOKEN_BOT_TELEGRAM", "token123")
        assert set(validar_env_vars()) == set(REQUIRED_ENV_VARS) - {"TOKEN_BOT_TELEGRAM"}

    def test_variavel_vazia_considerada_faltando(self, monkeypatch):
        for var in REQUIRED_ENV_VARS:
            monkeypatch.setenv(var, "")
        assert set(validar_env_vars()) == set(REQUIRED_ENV_VARS)


class TestLogEnvValidation:
    """Testes para a função log_env_validation()."""

    def test_log_ok_quando_sem_faltando(self, caplog):
        with caplog.at_level(logging.INFO):
            log_env_validation([])
        assert "Todas as variáveis de ambiente obrigatórias estão definidas" in caplog.text

    def test_log_erro_quando_com_faltando(self, caplog):
        with caplog.at_level(logging.ERROR):
            log_env_validation(["TOKEN_BOT_TELEGRAM", "CAM_WEB"])
        assert "Variáveis de ambiente faltando" in caplog.text
        assert "TOKEN_BOT_TELEGRAM" in caplog.text
        assert "CAM_WEB" in caplog.text
