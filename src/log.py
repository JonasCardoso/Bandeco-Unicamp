"""Módulo de gerenciamento de logs com envio para canal Telegram.

Este módulo fornece uma classe Log para registrar mensagens em diferentes níveis
de severidade e enviá-las para um canal do Telegram configurado.
"""

import logging
from enum import IntEnum

from telegram_servico import mandar_mensagem
from util import get_id_log_channel

# =============================================================================
# Constantes e configurações
# =============================================================================

logger = logging.getLogger(__name__)


class LogLevel(IntEnum):
    """Níveis de severidade para logs (valores inteiros para comparação)."""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class Log:
    """Gerenciador de logs com envio para Telegram.

    Attributes:
        _channel_id: ID do canal no Telegram para envio de logs.
        _log: Mensagem acumulada do log atual.
        _nivel: Nível mínimo de severidade para registro.
    """

    # Atributos padrão (podem ser sobrescritos por subclasses)
    _channel_id = ""
    _log = ""
    _nivel = LogLevel.INFO

    def __init__(self, nivel=None):
        """Inicializa o gerenciador de logs.

        Args:
            nivel: Nível mínimo de severidade. Se None, usa INFO por padrão.
        """
        # Usa atributos de instância para evitar problemas com name mangling
        self._log = ""  # Reset para cada nova instância
        if nivel is not None:
            self._nivel = nivel

    def _log_python(self, nivel, mensagem):
        """Registra no logger Python padrão."""
        logger.log(nivel.value, f"[Bandeco] {mensagem}")

    async def enviar_log(self, context):
        """Envia o log acumulado para o canal do Telegram e limpa.

        Args:
            context: CallbackContext do telegram-bot.

        Returns:
            True se o log foi enviado com sucesso, False caso contrário.
        """
        if self._log != "":
            try:
                channel_id = get_id_log_channel() or self._channel_id
                await mandar_mensagem(context, channel_id, self._log, None, None, "HTML")
                self.limpar_log()  # Limpa após envio bem-sucedido
                return True
            except Exception:
                logger.exception("Falha ao enviar log ao canal")
                return False
        return False

    def limpar_log(self):
        """Limpa o log acumulado."""
        self._log = ""

    def adicionar_log(self, mensagem, nivel=LogLevel.INFO):
        """Adiciona uma entrada ao log.

        Args:
            mensagem: Mensagem do log.
            nivel: Nível de severidade da mensagem.
        """
        if nivel.value >= self._nivel.value:
            prefixos = {
                LogLevel.DEBUG: "🐛 DEBUG",
                LogLevel.INFO: "ℹ️ INFO",
                LogLevel.WARNING: "⚠️ WARNING",
                LogLevel.ERROR: "❌ ERROR",
                LogLevel.CRITICAL: "🔥 CRITICAL",
            }
            prefixo = prefixos.get(nivel, "")
            self._log += f"{prefixo} - {mensagem}\n"
            self._log_python(nivel, mensagem)

    def debug(self, mensagem):
        """Registra um log de nível DEBUG."""
        self.adicionar_log(mensagem, LogLevel.DEBUG)

    def info(self, mensagem):
        """Registra um log de nível INFO."""
        self.adicionar_log(mensagem, LogLevel.INFO)

    def warning(self, mensagem):
        """Registra um log de nível WARNING."""
        self.adicionar_log(mensagem, LogLevel.WARNING)

    def error(self, mensagem):
        """Registra um log de nível ERROR."""
        self.adicionar_log(mensagem, LogLevel.ERROR)

    def critical(self, mensagem):
        """Registra um log de nível CRITICAL."""
        self.adicionar_log(mensagem, LogLevel.CRITICAL)
