"""Logging estruturado com entrega segura ao canal de diagnóstico do Telegram."""

from __future__ import annotations

import asyncio
import logging
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, Mapping

from telegram.error import NetworkError, RetryAfter, TelegramError, TimedOut

from core.config import get_id_log_channel
from core.settings import get_settings, valores_sensiveis

logger = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT = 4000
MAX_BUFFER_ENTRIES = 200
MAX_SEND_ATTEMPTS = 3
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(token|cookie|password|senha|secret|api[_-]?key|authorization)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)


class LogLevel(IntEnum):
    """Níveis aceitos pelo logger local e pelo canal Telegram."""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    @classmethod
    def from_name(cls, value: str, default: "LogLevel" = None) -> "LogLevel":
        fallback = default or cls.INFO
        return cls.__members__.get(str(value).upper(), fallback)


_PREFIXES = {
    LogLevel.DEBUG: "🐛 DEBUG",
    LogLevel.INFO: "ℹ️ INFO",
    LogLevel.WARNING: "⚠️ WARNING",
    LogLevel.ERROR: "❌ ERROR",
    LogLevel.CRITICAL: "🔥 CRITICAL",
}


def sanitizar_texto(value: Any) -> str:
    """Remove segredos conhecidos e atribuições sensíveis de um valor."""
    texto = str(value)
    try:
        segredos = sorted(valores_sensiveis(), key=len, reverse=True)
    except (OSError, ValueError):
        segredos = ()
    for segredo in segredos:
        if len(segredo) >= 4:
            texto = texto.replace(segredo, "[REDACTED]")
    return _SENSITIVE_ASSIGNMENT.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", texto)


def dividir_mensagem(texto: str, limite: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Divide texto sem exceder o limite conservador do Telegram."""
    if not texto:
        return []
    partes: list[str] = []
    restante = texto
    limite_conteudo = max(1, limite - 32)
    while len(restante) > limite_conteudo:
        corte = restante.rfind("\n", 0, limite_conteudo + 1)
        if corte <= 0:
            corte = limite_conteudo
        partes.append(restante[:corte])
        restante = restante[corte:].lstrip("\n")
    if restante:
        partes.append(restante)
    if len(partes) > 1:
        total = len(partes)
        partes = [f"[parte {indice}/{total}]\n{parte}" for indice, parte in enumerate(partes, 1)]
    return partes


@dataclass(frozen=True)
class LogEntry:
    """Entrada imutável pronta para renderização em texto simples."""

    level: LogLevel
    message: str
    component: str = "app"
    event: str = "event"
    context: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())

    def render(self) -> str:
        contexto = " ".join(
            f"{sanitizar_texto(chave)}={sanitizar_texto(valor)}"
            for chave, valor in sorted(self.context.items())
            if valor is not None
        )
        cabecalho = (
            f"{_PREFIXES[self.level]} - {sanitizar_texto(self.message)}"
            f"\n[{self.created_at.isoformat(timespec='seconds')}]"
            f" [{sanitizar_texto(self.component)}:{sanitizar_texto(self.event)}]"
        )
        return f"{cabecalho} {contexto}".rstrip()


class TelegramLogSink:
    """Entrega blocos ao Telegram com retries apenas para falhas transitórias."""

    async def send(self, context, channel_id: str, text: str) -> bool:
        for attempt in range(1, MAX_SEND_ATTEMPTS + 1):
            try:
                await context.bot.send_message(chat_id=channel_id, text=text, parse_mode=None)
                return True
            except RetryAfter as error:
                if attempt == MAX_SEND_ATTEMPTS:
                    break
                delay = error.retry_after
                if hasattr(delay, "total_seconds"):
                    delay = delay.total_seconds()
                await asyncio.sleep(max(float(delay), 0.0))
            except (TimedOut, NetworkError):
                if attempt == MAX_SEND_ATTEMPTS:
                    break
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
            except TelegramError:
                logger.warning("Falha permanente ao enviar log ao canal Telegram.", exc_info=True)
                return False
            except Exception:
                logger.exception("Falha inesperada ao enviar log ao canal Telegram.")
                return False
        logger.warning("Falha transitória persistente ao enviar log ao canal Telegram.")
        return False


class Log:
    """Buffer estruturado compatível com a antiga API de logs."""

    _channel_id = ""

    def __init__(self, nivel: LogLevel | None = None, sink: TelegramLogSink | None = None):
        configured = LogLevel.from_name(get_settings().telegram_log_level)
        self._nivel = nivel if nivel is not None else configured
        self._entries: deque[LogEntry] = deque()
        self._pending_chunks: deque[str] = deque()
        self._dropped = 0
        self._sink = sink or TelegramLogSink()

    @property
    def _log(self) -> str:
        partes = [*self._pending_chunks, *(entry.render() for entry in self._entries)]
        return "\n".join(partes)

    @_log.setter
    def _log(self, value: str) -> None:
        if value == "":
            self.limpar_log()
        elif value:
            self.adicionar_log(value)

    def _append(self, entry: LogEntry) -> None:
        if len(self._entries) >= MAX_BUFFER_ENTRIES:
            indice = next(
                (pos for pos, item in enumerate(self._entries) if item.level < LogLevel.ERROR),
                0,
            )
            del self._entries[indice]
            self._dropped += 1
        self._entries.append(entry)

    def adicionar_log(
        self,
        mensagem,
        nivel: LogLevel = LogLevel.INFO,
        *,
        component: str = "app",
        event: str = "event",
        context: Mapping[str, Any] | None = None,
    ) -> None:
        """Adiciona uma entrada, respeitando o nível mínimo configurado."""
        if nivel < self._nivel:
            return
        entry = LogEntry(nivel, str(mensagem), component, event, context or {})
        self._append(entry)
        logger.log(nivel.value, "[Bandeco] %s", entry.render())

    def _prepare_pending(self) -> None:
        if self._pending_chunks or not self._entries:
            return
        linhas = []
        if self._dropped:
            linhas.append(f"⚠️ WARNING - {self._dropped} entrada(s) descartada(s) por limite de buffer.")
        linhas.extend(entry.render() for entry in self._entries)
        self._pending_chunks.extend(dividir_mensagem("\n\n".join(linhas)))
        self._entries.clear()
        self._dropped = 0

    async def enviar_log(self, context) -> bool:
        """Envia o buffer; blocos não confirmados permanecem pendentes."""
        self._prepare_pending()
        if not self._pending_chunks:
            return False
        try:
            channel_id = get_id_log_channel() or self._channel_id
        except (OSError, ValueError):
            logger.exception("Canal de logs do Telegram não está configurado.")
            return False

        while self._pending_chunks:
            if not await self._sink.send(context, channel_id, self._pending_chunks[0]):
                return False
            self._pending_chunks.popleft()
        return True

    def limpar_log(self) -> None:
        self._entries.clear()
        self._pending_chunks.clear()
        self._dropped = 0

    def debug(self, mensagem, **kwargs) -> None:
        self.adicionar_log(mensagem, LogLevel.DEBUG, **kwargs)

    def info(self, mensagem, **kwargs) -> None:
        self.adicionar_log(mensagem, LogLevel.INFO, **kwargs)

    def warning(self, mensagem, **kwargs) -> None:
        self.adicionar_log(mensagem, LogLevel.WARNING, **kwargs)

    def error(self, mensagem, **kwargs) -> None:
        self.adicionar_log(mensagem, LogLevel.ERROR, **kwargs)

    def critical(self, mensagem, **kwargs) -> None:
        self.adicionar_log(mensagem, LogLevel.CRITICAL, **kwargs)


async def tratar_erro_aplicacao(update, context) -> None:
    """Registra exceções não tratadas sem enviar traceback ou segredos ao canal."""
    error = context.error
    logger.error(
        "Exceção não tratada pelo Telegram.",
        exc_info=(type(error), error, error.__traceback__) if error else None,
    )
    update_id = getattr(update, "update_id", None)
    log = Log(nivel=LogLevel.ERROR)
    log.error(
        type(error).__name__ if error else "UnknownError",
        component="telegram",
        event="unhandled_error",
        context={"update_id": update_id},
    )
    await log.enviar_log(context)
