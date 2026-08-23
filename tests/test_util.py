"""Testes unitários para utilitários (util.py)."""
from unittest.mock import patch

import pytest
import requests

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
        assert "Ativo" in verificar_atividade(dados, 'cafe')

    def test_retorna_inativo_quando_falso(self):
        dados = {"almoco": 0}
        assert "Inativo" in verificar_atividade(dados, 'almoco')


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
        with patch.dict('os.environ', {'TEST_VAR_EXISTENTE': 'valor_teste'}):
            result = _require_env('TEST_VAR_EXISTENTE')
            assert result == 'valor_teste'

    def test_require_env_variavel_inexistente(self):
        # Garante que a variável não existe
        env_copy = dict(__import__('os').environ)
        if 'TEST_VAR_INEXISTENTE' in env_copy:
            del env_copy['TEST_VAR_INEXISTENTE']
        with patch.dict('os.environ', env_copy, clear=False):
            original = __import__('os').environ.pop('TEST_VAR_INEXISTENTE', None)
            try:
                with pytest.raises(ValueError, match="Variável de ambiente obrigatória"):
                    _require_env('TEST_VAR_INEXISTENTE')
            finally:
                if original is not None:
                    __import__('os').environ['TEST_VAR_INEXISTENTE'] = original

    def test_get_env_retorna_none(self):
        # monkeypatch.setenv já definiu todas as vars, então vamos testar com uma que não existe
        result = _get_env('VARIAVEL_INEXISTENTE_TESTE_999')
        assert result is None  # Sem default, retorna None


class TestConstants:
    """Testes para constantes do módulo util."""

    def test_dias_contem_segunda_a_domingo(self):
        assert len(DIAS) == 7
        assert DIAS[0] == 'Segunda-feira'
        assert DIAS[-1] == 'Domingo'

    def test_modalidades_contem_tipos_esperados(self):
        assert len(MODALIDADES) == 5
        assert 'Almoço Tradicional' in MODALIDADES
        assert 'Almoço Vegano' in MODALIDADES
        assert 'Café da manhã' in MODALIDADES


# =============================================================================
# Testes para validar_env_vars e log_env_validation
# =============================================================================


class TestValidarEnvVars:
    """Testes para a função validar_env_vars()."""

    def test_retorna_lista_vazia_quando_todas_presentes(self, monkeypatch):
        vars_obrigatorias = [
            'TOKEN_BOT_TELEGRAM',
            'DATABASE_URL_FIREBASE',
            'CAM_WEB',
            'CAM_RU_A',
            'CAM_RU_B',
            'CAM_RA',
            'CAM_RS',
        ]
        for var in vars_obrigatorias:
            monkeypatch.setenv(var, 'valor')

        faltando = validar_env_vars()
        assert faltando == []

    def test_retorna_variaveis_faltando(self, monkeypatch):
        # Limpa todas as variáveis relevantes
        vars_obrigatorias = [
            'TOKEN_BOT_TELEGRAM',
            'DATABASE_URL_FIREBASE',
            'CAM_WEB',
            'CAM_RU_A',
            'CAM_RU_B',
            'CAM_RA',
            'CAM_RS',
        ]
        for var in vars_obrigatorias:
            monkeypatch.delenv(var, raising=False)

        # Define apenas algumas
        monkeypatch.setenv('TOKEN_BOT_TELEGRAM', 'token123')
        monkeypatch.setenv('DATABASE_URL_FIREBASE', 'https://exemplo.com')

        faltando = validar_env_vars()

        assert 'CAM_WEB' in faltando
        assert 'CAM_RU_A' in faltando
        assert 'TOKEN_BOT_TELEGRAM' not in faltando
        assert 'DATABASE_URL_FIREBASE' not in faltando

    def test_variavel_vazia_considerada_faltando(self, monkeypatch):
        vars_obrigatorias = [
            'TOKEN_BOT_TELEGRAM',
            'DATABASE_URL_FIREBASE',
            'CAM_WEB',
            'CAM_RU_A',
            'CAM_RU_B',
            'CAM_RA',
            'CAM_RS',
        ]
        for var in vars_obrigatorias:
            monkeypatch.setenv(var, '')

        faltando = validar_env_vars()

        assert len(faltando) == 7


class TestLogEnvValidation:
    """Testes para a função log_env_validation()."""

    def test_log_ok_quando_sem_faltando(self, capsys):
        log_env_validation([])
        captured = capsys.readouterr()
        assert 'Todas as variáveis de ambiente obrigatórias estão definidas' in captured.out

    def test_log_erro_quando_com_faltando(self, capsys):
        log_env_validation(['TOKEN_BOT_TELEGRAM', 'CAM_WEB'])
        captured = capsys.readouterr()
        assert 'Variáveis de ambiente faltando' in captured.out
        assert '- TOKEN_BOT_TELEGRAM' in captured.out
        assert '- CAM_WEB' in captured.out
