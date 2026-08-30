"""Configuração tipada e carregada de forma preguiçosa."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REQUIRED_ENV_VARS = (
    "TOKEN_BOT_TELEGRAM",
    "USERNAME_BOT_TELEGRAM",
    "ID_LOG_CHANNEL",
    "DATABASE_URL_FIREBASE",
)


class Settings(BaseSettings):
    """Configuração do bot; integrações opcionais são validadas quando usadas."""

    horario_cafe: int = 6
    horario_almoco: int = 10
    horario_jantar: int = 17

    token_bot_telegram: Optional[str] = None
    username_bot_telegram: Optional[str] = None
    id_log_channel: Optional[str] = None

    url_bandeco_prefeitura: str = "https://sistemas.prefeitura.unicamp.br/apps/cardapio/index.php?d="
    url_bandeco_json: str = "https://www1.sistemas.prefeitura.unicamp.br/Mobile/CardapioPrefeituraCampinasJSON"
    url_horario: str = "https://prefeitura.unicamp.br/produto/restaurantes-universitarios/#horario"
    url_valor_refeicao_cafe: str = "https://prefeitura.unicamp.br/produto/valor-da-refeicao-cafe-da-manha/"
    url_valor_refeicao_almoco: str = "https://prefeitura.unicamp.br/produto/valor-da-refeicao-almoco-e-jantar/"
    url_saldo: str = "https://www1.sistemas.prefeitura.unicamp.br/Mobile/ConsultaSaldo"

    database_url_firebase: Optional[str] = None
    firebase_json: Optional[str] = Field(default=None, repr=False)

    api_key_twitter: Optional[str] = None
    api_key_secret_twitter: Optional[str] = None
    bearer_token_twitter: Optional[str] = None
    access_token_twitter: Optional[str] = None
    access_token_secret_twitter: Optional[str] = None

    cam_web: str = "https://webservices.prefeitura.unicamp.br/cameras/cam_"
    cam_ru_a: str = "ru_a2"
    cam_ru_b: str = "ru_b2"
    cam_ra: str = "ra2"
    cam_rs: str = "rs2"
    cam_is_json: bool = False

    meta_page_access_token: Optional[str] = Field(default=None, repr=False)
    meta_graph_api_version: Literal["v26.0"] = "v26.0"
    instagram_user_id: Optional[str] = None
    facebook_page_id: Optional[str] = None

    r2_account_id: Optional[str] = None
    r2_access_key_id: Optional[str] = Field(default=None, repr=False)
    r2_secret_access_key: Optional[str] = Field(default=None, repr=False)
    r2_bucket: Optional[str] = None
    hf_token: Optional[str] = Field(default=None, repr=False)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna uma única configuração, criada somente no primeiro uso."""
    return Settings()


def clear_settings_cache() -> None:
    """Invalida a configuração; destinado a testes e reload explícito."""
    get_settings.cache_clear()


def validar_variaveis_obrigatorias(settings: Optional[Settings] = None) -> list[str]:
    """Retorna os nomes das configurações essenciais ausentes ou vazias."""
    config = settings or Settings()
    return [nome for nome in REQUIRED_ENV_VARS if not getattr(config, nome.lower())]
