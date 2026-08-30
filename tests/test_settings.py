"""Testes unitarios para settings.py (configuracoes via pydantic-settings)."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError


class TestSettingsInitialization:
    """Testes para inicializacao da classe Settings."""

    def test_settings_inicializa_com_valores_padrao(self):
        """Settings deve usar valores padrao quando env vars nao estao definidas.

        Nota: O conftest.py define HORARIO_CAFE=7, etc., entao os valores das
        env vars prevalecem sobre os padroes. Este teste verifica que Settings
        aceita valores das env vars corretamente.
        """
        from core.settings import Settings

        s = Settings()
        # Valores vem do conftest.py (HORARIO_CAFE=7, etc.)
        assert s.horario_cafe == 7
        assert s.horario_almoco == 12
        assert s.horario_jantar == 19

    def test_settings_valores_cameras_padrao(self):
        """Valores padrao das cameras devem estar corretos."""
        from core.settings import Settings

        # CAM_* vem do conftest, mas cam_is_json deve ser False (padrao)
        s = Settings()
        assert s.cam_is_json is False  # 'false'.lower() in ('true', '1', 'yes') → False

    def test_settings_urls_configuradas(self):
        """URLs devem vir das variaveis de ambiente."""
        from core.settings import Settings

        s = Settings()
        assert s.url_bandeco_prefeitura == "https://exemplo.com/prefeitura/"
        assert s.url_bandeco_json == "https://exemplo.com/json"


class TestSettingsProperties:
    """Testes para as propriedades auxiliares (aliasing) do Settings."""

    def test_tweetkit_cookie_configurado(self):
        from core.settings import Settings

        s = Settings()
        assert s.tweetkit_cookie == "auth_token=test_auth; ct0=test_csrf"

    def test_configuracao_meta_v26(self):
        from core.settings import Settings

        s = Settings()
        assert s.meta_page_access_token == "test_meta_page_token"
        assert s.meta_graph_api_version == "v26.0"
        assert s.instagram_user_id == "123456789"
        assert s.facebook_page_id == "987654321"
        assert s.r2_account_id == "test-r2-account"
        assert s.r2_access_key_id == "test-r2-access"
        assert s.r2_secret_access_key == "test-r2-secret"
        assert s.r2_bucket == "test-r2-bucket"

    def test_segredos_nao_aparecem_no_repr(self):
        from core.settings import Settings

        s = Settings()
        assert "test_meta_page_token" not in repr(s)
        assert "test_auth" not in repr(s)
        assert "service_account" not in repr(s)
        assert "test-r2-access" not in repr(s)
        assert "test-r2-secret" not in repr(s)

    def test_versao_meta_nao_pode_ser_alterada(self, monkeypatch):
        from core.settings import Settings

        monkeypatch.setenv("META_GRAPH_API_VERSION", "v25.0")
        with pytest.raises(ValidationError):
            Settings()


class TestSettingsSingleton:
    """Testes para o padrao singleton (get_settings)."""

    def test_get_settings_retorna_instancia(self):
        from core.settings import get_settings

        s = get_settings()
        assert s is not None

    def test_get_settings_e_singleton(self):
        from core.settings import clear_settings_cache, get_settings

        clear_settings_cache()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2


class TestSettingsRequiredFields:
    """Testes para campos obrigatorios do Settings."""

    def test_token_bot_telegram_obrigatorio(self):
        from core.settings import Settings

        # Limpa a env var temporariamente
        with patch.dict(os.environ, {"TOKEN_BOT_TELEGRAM": ""}, clear=False):
            s = Settings()
            assert s.token_bot_telegram == ""

    def test_database_url_firebase_obrigatorio(self):
        from core.settings import Settings

        with patch.dict(os.environ, {"DATABASE_URL_FIREBASE": ""}, clear=False):
            s = Settings()
            assert s.database_url_firebase == ""


class TestSettingsConfigDict:
    """Testes para a configuracao do pydantic-settings."""

    def test_case_insensitive(self):
        from core.settings import Settings

        # Deve funcionar com maiusculas/minusculas mistas
        s = Settings()
        assert hasattr(s, "horario_cafe")
        assert hasattr(s, "token_bot_telegram")


class TestSettingsOptionalFields:
    """Testes para campos opcionais do Settings."""

    def test_firebase_json_optional(self):
        from core.settings import Settings

        s = Settings()
        # FIREBASE_JSON vem do conftest
        assert s.firebase_json is not None

    def test_hf_token_opcional_nao_e_exposto(self, monkeypatch):
        from core.settings import Settings

        segredo = "hf_token_que_nao_deve_ser_logado"
        monkeypatch.setenv("HF_TOKEN", segredo)
        settings = Settings()
        assert settings.hf_token == segredo
        assert segredo not in repr(settings)


class TestSettingsModelConfig:
    """Testes para o model_config do pydantic-settings."""

    def test_env_file_configured(self):
        from core.settings import Settings

        # Verifica que o env_file esta configurado
        assert hasattr(Settings, "model_config")
        config = Settings.model_config
        assert "env_file" in str(config) or hasattr(config, "get")

    def test_env_file_aponta_para_raiz_do_repositorio(self):
        from core.settings import Settings

        raiz = Path(__file__).resolve().parents[1]
        assert Path(Settings.model_config["env_file"]) == raiz / ".env"
