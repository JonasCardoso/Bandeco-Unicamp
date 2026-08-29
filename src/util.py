"""Módulo de utilitários gerais e constantes do projeto.

Este módulo contém:
- Funções utilitárias (verificar_atividade, salvar_json)
- Decorator de retry para chamadas externas
- Constantes do projeto (dias, modalidades, paths)
- Variáveis de ambiente validadas via lazy loading (funções getter com cache)
"""

import asyncio
import inspect
import json
import logging
import os
import threading
import time
from functools import lru_cache, wraps
from typing import Any, Callable, Optional, Tuple

from constants import (
    DIAS as DIAS,
)
from constants import (
    MODALIDADES as MODALIDADES,
)
from constants import (
    PATH_FONTE_LATO_BOLD as PATH_FONTE_LATO_BOLD,
)
from constants import (
    PATH_FONTE_LATO_MEDIUM as PATH_FONTE_LATO_MEDIUM,
)
from settings import Settings, validar_variaveis_obrigatorias

logger = logging.getLogger(__name__)

# =============================================================================
# Utilitários
# =============================================================================


def verificar_atividade(dados: dict, campo: str) -> str:
    """Verifica se um campo está ativo ou inativo nos dados.

    Args:
        dados: Dicionário com os dados do usuário.
        campo: Nome do campo a ser verificado.

    Returns:
        'Ativo' se verdadeiro, 'Inativo' caso contrário.
    """
    return "Inativo" if not dados[campo] else "Ativo"


def salvar_json(dados: Any, nome: str) -> None:
    """Salva dados em um arquivo JSON.

    Args:
        dados: Dados a serem salvos (deve ser serializável).
        nome: Nome do arquivo (sem extensão).
    """
    with open(f"{nome}.json", "w", encoding="utf-8") as f:
        json.dump(json.loads(dados), f, ensure_ascii=False, indent=4)


# =============================================================================
# Retry decorator para chamadas externas
# =============================================================================


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[type[BaseException], ...] = (Exception,),
) -> Callable:
    """Repete funções síncronas ou assíncronas com backoff exponencial."""
    if max_attempts < 1:
        raise ValueError("max_attempts deve ser maior ou igual a 1")

    def decorator(func: Callable) -> Callable:
        def registrar_tentativa(attempt: int, erro: BaseException) -> None:
            espera = delay * (2**attempt)
            logger.warning(
                "%s falhou (tentativa %s/%s): %s; nova tentativa em %.1fs",
                func.__name__,
                attempt + 1,
                max_attempts,
                erro,
                espera,
            )

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as erro:
                        if attempt == max_attempts - 1:
                            logger.error("%s falhou após %s tentativas", func.__name__, max_attempts)
                            raise
                        registrar_tentativa(attempt, erro)
                        await asyncio.sleep(delay * (2**attempt))

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as erro:
                    if attempt == max_attempts - 1:
                        logger.error("%s falhou após %s tentativas", func.__name__, max_attempts)
                        raise
                    registrar_tentativa(attempt, erro)
                    time.sleep(delay * (2**attempt))

        return sync_wrapper

    return decorator


# =============================================================================
# Validação de variáveis de ambiente no startup
# =============================================================================


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
        value = getattr(Settings(), campo)
    else:
        value = _get_env(name)
    if value is None or value == "":
        raise ValueError(f"Variável de ambiente obrigatória não definida: '{name}'. Verifique o arquivo .env.")
    return value


# --- Horários do bot (lazy loading) ---


@lru_cache(maxsize=None)
def get_horario_cafe() -> int:
    """Retorna o horário de café (formato 24h)."""
    return int(_require_env("HORARIO_CAFE"))


@lru_cache(maxsize=None)
def get_horario_almoco() -> int:
    """Retorna o horário do almoço (formato 24h)."""
    return int(_require_env("HORARIO_ALMOCO"))


@lru_cache(maxsize=None)
def get_horario_jantar() -> int:
    """Retorna o horário do jantar (formato 24h)."""
    return int(_require_env("HORARIO_JANTAR"))


# --- Telegram (lazy loading) ---


@lru_cache(maxsize=None)
def get_token_bot_telegram() -> str:
    """Retorna o token do bot do Telegram."""
    return _require_env("TOKEN_BOT_TELEGRAM")


@lru_cache(maxsize=None)
def get_id_log_channel() -> str:
    """Retorna o ID do canal de logs no Telegram."""
    return _require_env("ID_LOG_CHANNEL")


# --- URLs Bandeco (lazy loading) ---


@lru_cache(maxsize=None)
def get_url_bandeco_prefeitura() -> str:
    """Retorna a URL da API Bandeco Prefeitura."""
    return _require_env("URL_BANDECO_PREFEITURA")


@lru_cache(maxsize=None)
def get_url_bandeco_json() -> str:
    """Retorna a URL da API JSON Bandeco."""
    return _require_env("URL_BANDECO_JSON")


@lru_cache(maxsize=None)
def get_url_horario() -> str:
    """Retorna a URL de horários dos restaurantes universitários."""
    return _require_env("URL_HORARIO")


@lru_cache(maxsize=None)
def get_url_valor_refeicao_cafe() -> str:
    """Retorna a URL da página de valores do café da manhã."""
    return _require_env("URL_VALOR_REFEICAO_CAFE")


@lru_cache(maxsize=None)
def get_url_valor_refeicao_almoco() -> str:
    """Retorna a URL da página de valores do almoço e jantar."""
    return _require_env("URL_VALOR_REFEICAO_ALMOCO")


@lru_cache(maxsize=None)
def get_url_saldo() -> str:
    """Retorna a URL de consulta de saldo Bandeco."""
    return _require_env("URL_SALDO")


# --- Firebase (lazy loading) ---


@lru_cache(maxsize=None)
def get_database_url_firebase() -> str:
    """Retorna a URL do banco de dados Firebase."""
    return _require_env("DATABASE_URL_FIREBASE")


@lru_cache(maxsize=None)
def get_firebase_json() -> str:
    """Retorna o JSON de credenciais do Firebase."""
    return _require_env("FIREBASE_JSON")


# --- Bot Telegram (lazy loading) ---


@lru_cache(maxsize=None)
def get_bot_username() -> str:
    """Retorna o username do bot Telegram."""
    return _require_env("USERNAME_BOT_TELEGRAM")


# --- Twitter/X (lazy loading) ---


@lru_cache(maxsize=None)
def get_api_key_twitter() -> str:
    """Retorna a API Key do Twitter."""
    return _require_env("API_KEY_TWITTER")


@lru_cache(maxsize=None)
def get_api_key_secret_twitter() -> str:
    """Retorna o API Key Secret do Twitter."""
    return _require_env("API_KEY_SECRET_TWITTER")


@lru_cache(maxsize=None)
def get_bearer_token_twitter() -> str:
    """Retorna o Bearer Token do Twitter."""
    return _require_env("BEARER_TOKEN_TWITTER")


@lru_cache(maxsize=None)
def get_access_token_twitter() -> str:
    """Retorna o Access Token do Twitter."""
    return _require_env("ACCESS_TOKEN_TWITTER")


@lru_cache(maxsize=None)
def get_access_token_secret_twitter() -> str:
    """Retorna o Access Token Secret do Twitter."""
    return _require_env("ACCESS_TOKEN_SECRET_TWITTER")


# --- Câmeras (lazy loading) ---


@lru_cache(maxsize=None)
def get_cam_web() -> str:
    """Retorna a URL base das câmeras web."""
    return _require_env("CAM_WEB")


@lru_cache(maxsize=None)
def get_cam_ru_a() -> str:
    """Retorna o identificador da câmera do RU A."""
    return _require_env("CAM_RU_A")


@lru_cache(maxsize=None)
def get_cam_ru_b() -> str:
    """Retorna o identificador da câmera do RU B."""
    return _require_env("CAM_RU_B")


@lru_cache(maxsize=None)
def get_cam_ra() -> str:
    """Retorna o identificador da câmera RA."""
    return _require_env("CAM_RA")


@lru_cache(maxsize=None)
def get_cam_rs() -> str:
    """Retorna o identificador da câmera RS."""
    return _require_env("CAM_RS")


@lru_cache(maxsize=None)
def get_cam_is_json() -> bool:
    """Retorna True se as câmeras usam formato JSON."""
    value = _require_env("CAM_IS_JSON")
    return value if isinstance(value, bool) else value.lower() in ("true", "1", "yes")


# --- Meta (Instagram/Facebook) (lazy loading) ---


@lru_cache(maxsize=None)
def get_instagram_access_token() -> str:
    """Retorna o Access Token do Instagram."""
    return _require_env("INSTAGRAM_ACCESS_TOKEN")


@lru_cache(maxsize=None)
def get_facebook_access_token() -> str:
    """Retorna o Access Token do Facebook."""
    return _require_env("FACEBOOK_ACCESS_TOKEN")


@lru_cache(maxsize=None)
def get_instagram_user_id() -> str:
    """Retorna o User ID do Instagram."""
    return _require_env("INSTAGRAM_USER_ID")


@lru_cache(maxsize=None)
def get_facebook_user_id() -> str:
    """Retorna o User ID do Facebook."""
    return _require_env("FACEBOOK_USER_ID")


@lru_cache(maxsize=None)
def get_graph_url() -> str:
    """Retorna a URL da API Graph do Facebook/Instagram."""
    return _require_env("GRAPH_URL")


# --- Ngrok (lazy loading) ---


@lru_cache(maxsize=None)
def get_token_ngrok() -> str:
    """Retorna o token de autenticação do ngrok."""
    return _require_env("TOKEN_NGROK")


# =============================================================================
# Rate Limiter por chave (simples, em memória)
# =============================================================================


class RateLimiter:
    """Rate limiter simples baseado em janela deslizante.

    Attributes:
        max_calls: Número máximo de chamadas permitidas no window.
        window_seconds: Tamanho da janela em segundos.
    """

    def __init__(self, max_calls: int = 5, window_seconds: float = 60.0):
        self._max_calls = max_calls
        self._window_seconds = window_seconds
        self._calls: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        """Verifica se a chamada para 'key' está dentro do limite.

        Returns:
            True se permitido, False se excedeu o rate limit.
        """
        now = time.time()
        with self._lock:
            if key not in self._calls:
                self._calls[key] = []

            # Remove timestamps fora da janela atual
            cutoff = now - self._window_seconds
            self._calls[key] = [t for t in self._calls[key] if t > cutoff]

            if len(self._calls[key]) >= self._max_calls:
                return False

            self._calls[key].append(now)
            return True


# Instância global para consultas à API de cardápio (mais restrita)
rate_limiter_cardapio = RateLimiter(max_calls=15, window_seconds=60.0)

# Instância global para consulta de saldo (um pouco mais permissiva)
rate_limiter_saldo = RateLimiter(max_calls=5, window_seconds=60.0)
