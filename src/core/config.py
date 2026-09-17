"""Acesso tipado e preguiçoso à configuração da aplicação."""

import logging
import os
from typing import Any, Optional

from .settings import Settings, get_settings, validar_variaveis_obrigatorias

logger = logging.getLogger(__name__)


def validar_env_vars() -> list[str]:
    """Valida se todas as variáveis de ambiente obrigatórias estão definidas.

    Returns:
        Lista com os nomes das variáveis faltando (vazia se tudo OK).
    """
    return validar_variaveis_obrigatorias()


def log_env_validation(faltando: list[str]) -> None:
    """Loga o resultado da validação de variáveis de ambiente.

    Args:
        faltando: Lista com as variáveis faltando.
    """
    if not faltando:
        logger.info("Todas as variáveis de ambiente obrigatórias estão definidas.")
        return
    logger.error("Variáveis de ambiente faltando: %s", ", ".join(faltando))


# =============================================================================
# Variáveis de ambiente (lazy loading com cache)
# =============================================================================
# As variáveis abaixo são carregadas sob demanda via funções getter.
# Isso evita falhas durante o import quando nenhuma delas é necessária.
# O @lru_cache garante que cada variável seja lida apenas uma vez.


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Retorna uma variável de ambiente respeitando o default informado."""
    return os.environ.get(name, default)


def _require_env(name: str) -> Any:
    """Obtém configuração tipada e rejeita valor ausente ou vazio."""
    campo = name.lower()
    if campo in Settings.model_fields:
        value = getattr(get_settings(), campo)
    else:
        value = _get_env(name)
    if value is None or value == "":
        raise ValueError(f"Variável de ambiente obrigatória não definida: '{name}'. Verifique o arquivo .env.")
    return value


# --- Horários do bot (lazy loading) ---


def get_horario_cafe() -> int:
    """Retorna o horário de café (formato 24h)."""
    return int(_require_env("HORARIO_CAFE"))


def get_horario_almoco() -> int:
    """Retorna o horário do almoço (formato 24h)."""
    return int(_require_env("HORARIO_ALMOCO"))


def get_horario_jantar() -> int:
    """Retorna o horário do jantar (formato 24h)."""
    return int(_require_env("HORARIO_JANTAR"))


# --- Telegram (lazy loading) ---


def get_token_bot_telegram() -> str:
    """Retorna o token do bot do Telegram."""
    return _require_env("TOKEN_BOT_TELEGRAM")


def get_id_log_channel() -> str:
    """Retorna o ID do canal de logs no Telegram."""
    return _require_env("ID_LOG_CHANNEL")


# --- URLs Bandeco (lazy loading) ---


def get_url_bandeco_prefeitura() -> str:
    """Retorna a URL da API Bandeco Prefeitura."""
    return _require_env("URL_BANDECO_PREFEITURA")


def get_url_bandeco_json() -> str:
    """Retorna a URL da API JSON Bandeco."""
    return _require_env("URL_BANDECO_JSON")


def get_url_horario() -> str:
    """Retorna a URL de horários dos restaurantes universitários."""
    return _require_env("URL_HORARIO")


def get_url_valor_refeicao_cafe() -> str:
    """Retorna a URL da página de valores do café da manhã."""
    return _require_env("URL_VALOR_REFEICAO_CAFE")


def get_url_valor_refeicao_almoco() -> str:
    """Retorna a URL da página de valores do almoço e jantar."""
    return _require_env("URL_VALOR_REFEICAO_ALMOCO")


def get_url_saldo() -> str:
    """Retorna a URL de consulta de saldo Bandeco."""
    return _require_env("URL_SALDO")


# --- Firebase (lazy loading) ---


def get_database_url_firebase() -> str:
    """Retorna a URL do banco de dados Firebase."""
    return _require_env("DATABASE_URL_FIREBASE")


def get_firebase_json() -> str:
    """Retorna o JSON de credenciais do Firebase."""
    return _require_env("FIREBASE_JSON")


# --- Cloudflare R2 (lazy loading) ---


def get_r2_account_id() -> str:
    """Retorna o ID da conta Cloudflare usada pelo endpoint R2."""
    return _require_env("R2_ACCOUNT_ID")


def get_r2_access_key_id() -> str:
    """Retorna o identificador da credencial S3 do R2."""
    return _require_env("R2_ACCESS_KEY_ID")


def get_r2_secret_access_key() -> str:
    """Retorna o segredo da credencial S3 do R2."""
    return _require_env("R2_SECRET_ACCESS_KEY")


def get_r2_bucket() -> str:
    """Retorna o bucket R2 de mídias sociais temporárias."""
    return _require_env("R2_BUCKET")


# --- Bot Telegram (lazy loading) ---


def get_bot_username() -> str:
    """Retorna o username do bot Telegram."""
    return _require_env("USERNAME_BOT_TELEGRAM")


# --- Twitter/X via tweetkit_x (lazy loading) ---


def get_tweetkit_cookie() -> str:
    """Retorna o cookie de sessão usado pelo tweetkit_x."""
    return _require_env("TWEETKIT_COOKIE")


# --- Câmeras (lazy loading) ---


def get_cam_web() -> str:
    """Retorna a URL base das câmeras web."""
    return _require_env("CAM_WEB")


def get_cam_ru_a() -> str:
    """Retorna o identificador da câmera do RU A."""
    return _require_env("CAM_RU_A")


def get_cam_ru_b() -> str:
    """Retorna o identificador da câmera do RU B."""
    return _require_env("CAM_RU_B")


def get_cam_ra() -> str:
    """Retorna o identificador da câmera RA."""
    return _require_env("CAM_RA")


def get_cam_rs() -> str:
    """Retorna o identificador da câmera RS."""
    return _require_env("CAM_RS")


def get_cam_is_json() -> bool:
    """Retorna True se as câmeras usam formato JSON."""
    value = _require_env("CAM_IS_JSON")
    return value if isinstance(value, bool) else value.lower() in ("true", "1", "yes")


# --- Meta (Instagram/Facebook) (lazy loading) ---


def get_meta_page_access_token() -> str:
    """Retorna o Page Access Token compartilhado pelas APIs Meta."""
    return _require_env("META_PAGE_ACCESS_TOKEN")


def get_meta_graph_api_version() -> str:
    """Retorna a versão explicitamente fixada da Graph API."""
    return _require_env("META_GRAPH_API_VERSION")


def get_instagram_user_id() -> str:
    """Retorna o ID da conta profissional do Instagram."""
    return _require_env("INSTAGRAM_USER_ID")


def get_facebook_page_id() -> str:
    """Retorna o ID da Página do Facebook."""
    return _require_env("FACEBOOK_PAGE_ID")
