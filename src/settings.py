"""Configurações do ambiente via pydantic-settings.

Substitui o sistema antigo de variáveis de ambiente (util.py) por um schema
tipado e validado centralizado, com carregamento automático a partir de:
  1. Variáveis de ambiente
  2. Arquivo .env (se existir)

Uso:
    from settings import Settings
    settings = Settings()
    token = settings.token_bot_telegram
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover — fallback para ambientes sem pydantic-settings
    # Fallback mínimo: usa dict simples se pydantic-settings não estiver instalado
    class BaseSettings:  # type: ignore[no-redef]
        model_config = SettingsConfigDict  # type: ignore[name-defined]

        def __init__(self, **data: Any):  # noqa: D107
            self.__dict__.update(data)

    class SettingsConfigDict(dict):  # type: ignore[no-redef]
        pass


class Settings(BaseSettings):
    """Schema centralizado de configurações do Bandeco-Unicamp Bot.

    Todas as variáveis de ambiente são carregadas automaticamente.
    Campos opcionais têm valor padrão; campos obrigatórios levantam erro
    se não estiverem definidos.
    """

    # -------------------------------------------------------------------------
    # Horários (formato 24h)
    # -------------------------------------------------------------------------
    horario_cafe: int = 6
    horario_almoco: int = 10
    horario_jantar: int = 17

    # -------------------------------------------------------------------------
    # Telegram
    # -------------------------------------------------------------------------
    token_bot_telegram: str
    id_log_channel: str

    # -------------------------------------------------------------------------
    # URLs Bandeco
    # -------------------------------------------------------------------------
    url_bandeco_prefeitura: str = "https://sistemas.prefeitura.unicamp.br/apps/cardapio/index.php?d="
    url_bandeco_json: str = "https://www1.sistemas.prefeitura.unicamp.br/Mobile/CardapioPrefeituraCampinasJSON"
    url_horario: str = "https://prefeitura.unicamp.br/produto/restaurantes-universitarios/#horario"
    url_saldo: str = "https://www1.sistemas.prefeitura.unicamp.br/Mobile/ConsultaSaldo"

    # -------------------------------------------------------------------------
    # Firebase
    # -------------------------------------------------------------------------
    database_url_firebase: str
    firebase_json: Optional[str] = None  # JSON string ou caminho para arquivo

    # -------------------------------------------------------------------------
    # Twitter/X API v1.1
    # -------------------------------------------------------------------------
    api_key_twitter: Optional[str] = None
    api_key_secret_twitter: Optional[str] = None
    bearer_token_twitter: Optional[str] = None
    access_token_twitter: Optional[str] = None
    access_token_secret_twitter: Optional[str] = None

    # -------------------------------------------------------------------------
    # Câmeras dos RU
    # -------------------------------------------------------------------------
    cam_web: str = "https://webservices.prefeitura.unicamp.br/cameras/cam_"
    cam_ru_a: str = "ru_a2"
    cam_ru_b: str = "ru_b2"
    cam_ra: str = "ra2"
    cam_rs: str = "rs2"
    cam_is_json: bool = False

    # -------------------------------------------------------------------------
    # Meta (Instagram / Facebook)
    # -------------------------------------------------------------------------
    instagram_access_token: Optional[str] = None
    facebook_access_token: Optional[str] = None
    instagram_user_id: Optional[str] = None
    facebook_user_id: Optional[str] = None
    graph_url: str = "https://graph.facebook.com/v20.0/"

    # -------------------------------------------------------------------------
    # Ngrok
    # -------------------------------------------------------------------------
    token_ngrok: Optional[str] = None

    # -------------------------------------------------------------------------
    # IA (Groq)
    # -------------------------------------------------------------------------
    groq_access_token: Optional[str] = None

    # -------------------------------------------------------------------------
    # Configuração do pydantic-settings
    # -------------------------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Propriedades auxiliares (aliasing para compatibilidade)
    # -------------------------------------------------------------------------

    @property
    def API_KEY_TWITTER(self) -> str:
        return self.api_key_twitter or ""

    @property
    def API_KEY_SECRET_TWITTER(self) -> str:
        return self.api_key_secret_twitter or ""

    @property
    def BEARER_TOKEN_TWITTER(self) -> str:
        return self.bearer_token_twitter or ""

    @property
    def ACCESS_TOKEN_TWITTER(self) -> str:
        return self.access_token_twitter or ""

    @property
    def ACCESS_TOKEN_SECRET_TWITTER(self) -> str:
        return self.access_token_secret_twitter or ""

    @property
    def INSTAGRAM_ACCESS_TOKEN(self) -> str:
        return self.instagram_access_token or ""

    @property
    def FACEBOOK_ACCESS_TOKEN(self) -> str:
        return self.facebook_access_token or ""

    @property
    def INSTAGRAM_USER_ID(self) -> str:
        return self.instagram_user_id or ""

    @property
    def FACEBOOK_USER_ID(self) -> str:
        return self.facebook_user_id or ""


# Instância singleton — carregada preguiçosamente na primeira chamada
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Retorna a instância singleton de Settings (lazy loading)."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()  # type: ignore[call-arg]
    return _settings_instance
