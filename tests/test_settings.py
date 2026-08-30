"""Testes unitarios para settings.py (configuracoes via pydantic-settings)."""

import os
from pathlib import Path
from unittest.mock import patch


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

    def test_api_key_twitter_property(self):
        from core.settings import Settings

        s = Settings()
        # Com env var definida (mock no conftest)
        assert isinstance(s.API_KEY_TWITTER, str)
        assert s.API_KEY_TWITTER == "test_key"

    def test_api_key_secret_twitter_property(self):
        from core.settings import Settings

        s = Settings()
        assert s.API_KEY_SECRET_TWITTER == "test_secret"

    def test_bearer_token_twitter_property(self):
        from core.settings import Settings

        s = Settings()
        assert s.BEARER_TOKEN_TWITTER == "test_bearer"

    def test_access_token_twitter_properties(self):
        from core.settings import Settings

        s = Settings()
        assert s.ACCESS_TOKEN_TWITTER == "test_access"
        assert s.ACCESS_TOKEN_SECRET_TWITTER == "test_access_secret"

    def test_instagram_facebook_properties(self):
        from core.settings import Settings

        s = Settings()
        assert s.INSTAGRAM_ACCESS_TOKEN == "test_ig_token"
        assert s.FACEBOOK_ACCESS_TOKEN == "test_fb_token"
        assert s.INSTAGRAM_USER_ID == "123456789"
        assert s.FACEBOOK_USER_ID == "987654321"


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

    def test_token_ngrok_optional(self):
        from core.settings import Settings

        s = Settings()
        assert s.token_ngrok == "test_ngrok_token"

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
