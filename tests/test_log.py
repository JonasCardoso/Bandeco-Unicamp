"""Testes unitários para log.py (sistema de logging estruturado)."""

import pytest

from log import Log, LogLevel


class TestLogLevel:
    """Testes para a enumeração LogLevel."""

    def test_niveis_estao_ordenados(self):
        assert LogLevel.DEBUG.value < LogLevel.INFO.value
        assert LogLevel.INFO.value < LogLevel.WARNING.value
        assert LogLevel.WARNING.value < LogLevel.ERROR.value
        assert LogLevel.ERROR.value < LogLevel.CRITICAL.value


class TestLogClass:
    """Testes para a classe Log."""

    def test_inicializacao_padrao(self):
        log = Log()
        assert hasattr(log, "_log")
        assert hasattr(log, "_nivel")
        assert log._nivel == LogLevel.INFO

    def test_adicionar_log_info(self):
        log = Log()
        log.adicionar_log("Teste info", LogLevel.INFO)
        assert "ℹ️ INFO" in log._log or "INFO - Teste info" in log._log

    def test_adicionar_log_error(self):
        log = Log()
        log.adicionar_log("Erro crítico", LogLevel.ERROR)
        assert "❌ ERROR" in log._log or "ERROR - Erro crítico" in log._log

    def test_adicionar_log_warning(self):
        log = Log()
        log.adicionar_log("Aviso importante", LogLevel.WARNING)
        assert "⚠️ WARNING" in log._log or "WARNING - Aviso importante" in log._log

    def test_adicionar_log_debug(self):
        log = Log(nivel=LogLevel.DEBUG)
        log.adicionar_log("Debug info", LogLevel.DEBUG)
        assert "🐛 DEBUG" in log._log or "DEBUG - Debug info" in log._log

    def test_adicionar_log_critical(self):
        log = Log()
        log.adicionar_log("Falha total", LogLevel.CRITICAL)
        assert "🔥 CRITICAL" in log._log or "CRITICAL - Falha total" in log._log

    def test_filtro_de_nivel(self):
        log = Log(nivel=LogLevel.WARNING)
        log.adicionar_log("Debug ignorado", LogLevel.DEBUG)
        log.adicionar_log("Info ignorado", LogLevel.INFO)
        log.adicionar_log("Warning mantido", LogLevel.WARNING)
        log.adicionar_log("Error mantido", LogLevel.ERROR)

        assert "Debug ignorado" not in log._log
        assert "Info ignorado" not in log._log
        assert "Warning mantido" in log._log
        assert "Error mantido" in log._log

    def test_metodos_atalho(self):
        log = Log(nivel=LogLevel.DEBUG)
        log.debug("Debug msg")
        log.info("Info msg")
        log.warning("Warning msg")
        log.error("Error msg")
        log.critical("Critical msg")

        assert "DEBUG - Debug msg" in log._log
        assert "INFO - Info msg" in log._log
        assert "WARNING - Warning msg" in log._log
        assert "ERROR - Error msg" in log._log
        assert "CRITICAL - Critical msg" in log._log

    def test_limpar_log(self):
        log = Log()
        log.adicionar_log("Teste", LogLevel.INFO)
        assert len(log._log) > 0

        log.limpar_log()
        assert log._log == ""

    @pytest.mark.asyncio
    async def test_enviar_log_com_sucesso(self, mock_context):
        log = Log()
        log.adicionar_log("Mensagem de teste", LogLevel.INFO)

        result = await log.enviar_log(mock_context)

        assert result is True
        mock_context.bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_enviar_log_vazio_nao_envia(self, mock_context):
        log = Log()
        result = await log.enviar_log(mock_context)

        assert result is False
        mock_context.bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_enviar_log_limpa_apos_envio(self, mock_context):
        log = Log()
        log.adicionar_log("Mensagem antes", LogLevel.INFO)

        await log.enviar_log(mock_context)

        assert log._log == ""
