"""Testes unitários para modules.balance.service.py (consulta de saldo do cartão Bandeco)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.balance.service import saldo_bandeco


class TestSaldoBandeco:
    @pytest.mark.asyncio
    async def test_retry_em_erro_de_rede(self, mock_update, mock_context, mock_log):
        with (
            patch(
                "modules.balance.service.requests.post",
                side_effect=__import__("requests").RequestException("rede"),
            ) as requisicao,
            patch("shared.retry.time.sleep"),
        ):
            assert await saldo_bandeco(mock_update, mock_context, "123456", "senha", mock_log) is None
        assert requisicao.call_count == 3
        mock_log.enviar_log.assert_awaited_once()

    """Testes para a função saldo_bandeco()."""

    @pytest.mark.asyncio
    async def test_retorna_saldo_formatado_com_sucesso(self):
        mock_update = MagicMock()
        mock_update.effective_chat.id = 123456
        mock_update.effective_chat.full_name = "Test User"
        mock_update.effective_chat.username = "testuser"

        mock_context = MagicMock()
        mock_context.bot.send_message = AsyncMock()

        mock_log = MagicMock()
        mock_log.adicionar_log = MagicMock()
        mock_log.enviar_log = AsyncMock()

        # Mock da resposta da API com saldo válido
        mock_response = MagicMock()
        mock_response.json.return_value = {"cartao": [{"saldo": 150.75}]}

        with patch("modules.balance.service.requests.post", return_value=mock_response):
            with patch(
                "modules.balance.service.criptografar_senha",
                return_value=("md5hash", "sha256hash", "sha512hash"),
            ):
                result = await saldo_bandeco(mock_update, mock_context, "123456", "abc123", mock_log)

        assert result is not None
        assert "R$ 150,75" in result
        assert "123456" in result

    @pytest.mark.asyncio
    async def test_retorna_erro_para_credenciais_invalidas(self):
        mock_update = MagicMock()
        mock_update.effective_chat.id = 123456
        mock_update.effective_chat.full_name = "Test User"
        mock_update.effective_chat.username = "testuser"

        mock_context = MagicMock()
        mock_context.bot.send_message = AsyncMock()

        mock_log = MagicMock()
        mock_log.adicionar_log = MagicMock()
        mock_log.enviar_log = AsyncMock()

        # Mock da resposta com erro de autenticação
        mock_response = MagicMock()
        mock_response.json.return_value = {"erro": "Credenciais inválidas"}

        with patch("modules.balance.service.requests.post", return_value=mock_response):
            with patch(
                "modules.balance.service.criptografar_senha",
                return_value=("md5hash", "sha256hash", "sha512hash"),
            ):
                result = await saldo_bandeco(mock_update, mock_context, "123456", "senhainc", mock_log)

        assert result == "Usuário e/ou Senha Inválido(s)"

    @pytest.mark.asyncio
    async def test_saldo_com_valores_decimais_diferentes(self):
        mock_update = MagicMock()
        mock_update.effective_chat.id = 999999
        mock_update.effective_chat.full_name = "Test User"
        mock_update.effective_chat.username = "testuser"

        mock_context = MagicMock()
        mock_context.bot.send_message = AsyncMock()

        mock_log = MagicMock()
        mock_log.adicionar_log = MagicMock()
        mock_log.enviar_log = AsyncMock()

        # Testar saldo com .00 (sem decimais)
        mock_response = MagicMock()
        mock_response.json.return_value = {"cartao": [{"saldo": 50.0}]}

        with patch("modules.balance.service.requests.post", return_value=mock_response):
            with patch(
                "modules.balance.service.criptografar_senha",
                return_value=("md5hash", "sha256hash", "sha512hash"),
            ):
                result = await saldo_bandeco(mock_update, mock_context, "987654", "xyz789", mock_log)

        assert "R$ 50,00" in result

    @pytest.mark.asyncio
    async def test_saldo_zero(self):
        mock_update = MagicMock()
        mock_update.effective_chat.id = 111111
        mock_update.effective_chat.full_name = "Test User"
        mock_update.effective_chat.username = "testuser"

        mock_context = MagicMock()
        mock_context.bot.send_message = AsyncMock()

        mock_log = MagicMock()
        mock_log.adicionar_log = MagicMock()
        mock_log.enviar_log = AsyncMock()

        # Testar saldo zero
        mock_response = MagicMock()
        mock_response.json.return_value = {"cartao": [{"saldo": 0.0}]}

        with patch("modules.balance.service.requests.post", return_value=mock_response):
            with patch(
                "modules.balance.service.criptografar_senha",
                return_value=("md5hash", "sha256hash", "sha512hash"),
            ):
                result = await saldo_bandeco(mock_update, mock_context, "111111", "senhatest", mock_log)

        assert "R$ 0,00" in result
