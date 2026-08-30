"""Testes unitários para log.py (sistema de logging estruturado)."""

import pytest

from interfaces.telegram.logging import Log, LogLevel


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


class TestLogRobusto:
    def test_sanitiza_segredos_e_atribuicoes(self):
        from interfaces.telegram.logging import sanitizar_texto

        texto = sanitizar_texto("token=test_meta_page_token password=abacaxi")
        assert "test_meta_page_token" not in texto
        assert "abacaxi" not in texto
        assert texto.count("[REDACTED]") == 2

    def test_fragmentos_respeitam_limite(self):
        from interfaces.telegram.logging import dividir_mensagem

        partes = dividir_mensagem("linha longa " * 1000)
        assert len(partes) > 1
        assert all(len(parte) <= 4000 for parte in partes)
        assert partes[0].startswith("[parte 1/")

    @pytest.mark.asyncio
    async def test_falha_parcial_mantem_apenas_bloco_pendente(self, mock_context):
        class Sink:
            def __init__(self):
                self.resultados = iter([True, False, True])

            async def send(self, *_args):
                return next(self.resultados)

        log = Log(sink=Sink())
        log.info("x" * 5000)
        assert await log.enviar_log(mock_context) is False
        assert len(log._pending_chunks) == 1
        assert await log.enviar_log(mock_context) is True
        assert log._log == ""

    def test_limite_descarta_primeiro_entrada_de_baixa_severidade(self, monkeypatch):
        import interfaces.telegram.logging as modulo

        monkeypatch.setattr(modulo, "MAX_BUFFER_ENTRIES", 2)
        log = Log(nivel=LogLevel.DEBUG)
        log.info("ruído")
        log.error("erro")
        log.critical("crítico")
        assert "ruído" not in log._log
        assert "erro" in log._log
        assert "crítico" in log._log

    @pytest.mark.asyncio
    async def test_retry_transitorio_nao_perde_log(self, mock_context, monkeypatch):
        from unittest.mock import AsyncMock

        from telegram.error import TimedOut

        import interfaces.telegram.logging as modulo

        mock_context.bot.send_message.side_effect = [TimedOut(), None]
        monkeypatch.setattr(modulo.asyncio, "sleep", AsyncMock())
        log = Log()
        log.error("falha transitória")
        assert await log.enviar_log(mock_context) is True
        assert mock_context.bot.send_message.await_count == 2

    @pytest.mark.asyncio
    async def test_error_handler_envia_apenas_resumo(self, mock_context):
        from types import SimpleNamespace

        from interfaces.telegram.logging import tratar_erro_aplicacao

        mock_context.error = ValueError("password=segredo-interno")
        await tratar_erro_aplicacao(SimpleNamespace(update_id=42), mock_context)
        enviado = mock_context.bot.send_message.call_args.kwargs["text"]
        assert "ValueError" in enviado
        assert "segredo-interno" not in enviado
        assert "Traceback" not in enviado
