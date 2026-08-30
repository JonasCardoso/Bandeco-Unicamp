"""Testes unitários para interfaces.telegram.messaging.py."""

from unittest.mock import MagicMock, patch

import pytest
from telegram import ReplyKeyboardMarkup

from interfaces.telegram.messaging import (
    deletar_mensagem,
    mandar_imagem,
    mandar_mensagem,
    mandar_mensagem_teclado,
)


class TestMandarMensagem:
    """Testes para a função mandar_mensagem()."""

    @pytest.mark.asyncio
    async def test_envia_mensagem_com_sucesso(self, mock_context):
        await mandar_mensagem(mock_context, 123456, "Olá mundo")

        mock_context.bot.send_message.assert_called_once()
        call_kwargs = mock_context.bot.send_message.call_args
        assert call_kwargs.kwargs["chat_id"] == 123456
        assert call_kwargs.kwargs["text"] == "Olá mundo"
        assert call_kwargs.kwargs["parse_mode"] == "Markdown"

    @pytest.mark.asyncio
    async def test_envia_mensagem_com_parse_mode_html(self, mock_context):
        await mandar_mensagem(mock_context, 123456, "<b>bold</b>", parse_mode="HTML")

        call_kwargs = mock_context.bot.send_message.call_args
        assert call_kwargs.kwargs["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    async def test_envia_mensagem_com_reply_markup(self, mock_context):
        reply_markup = MagicMock(spec=ReplyKeyboardMarkup)

        await mandar_mensagem(mock_context, 123456, "Texto", reply_markup=reply_markup)

        call_kwargs = mock_context.bot.send_message.call_args
        assert call_kwargs.kwargs["reply_markup"] == reply_markup


class TestDeletarMensagem:
    """Testes para a função deletar_mensagem()."""

    @pytest.mark.asyncio
    async def test_deleta_mensagem_com_sucesso(self, mock_context):
        await deletar_mensagem(mock_context, 123456, 42)

        mock_context.bot.delete_message.assert_called_once_with(chat_id=123456, message_id=42)


class TestMandarImagem:
    """Testes para a função mandar_imagem()."""

    @pytest.mark.asyncio
    async def test_envia_imagem_com_sucesso(self, mock_context, tmp_path):
        # Cria um arquivo jpg temporário para simular a imagem
        fake_image = tmp_path / "test.jpg"
        fake_image.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        with patch("interfaces.telegram.messaging.pathlib.Path.resolve", return_value=str(tmp_path)):
            await mandar_imagem(mock_context, 123456, "test")

        mock_context.bot.send_photo.assert_called_once()


class TestMandarMensagemTeclado:
    """Testes para a função mandar_mensagem_teclado()."""

    @pytest.mark.asyncio
    async def test_envia_mensagem_com_teclado(self, mock_context):
        buttons = [[{"text": "Botão 1"}], [{"text": "Botão 2"}]]

        await mandar_mensagem_teclado(mock_context, 123456, "Selecione uma opção", buttons)

        mock_context.bot.send_message.assert_called_once()
        call_kwargs = mock_context.bot.send_message.call_args
        assert call_kwargs.kwargs["parse_mode"] == "Markdown"
        assert call_kwargs.kwargs["text"] == "Selecione uma opção"


class TestErrorHandling:
    """Testes para tratamento de erros nos serviços."""

    @pytest.mark.asyncio
    async def test_mandar_mensagem_erro_nao_propaga(self, mock_context):
        # Faz o bot.send_message levantar exceção
        mock_context.bot.send_message.side_effect = Exception("Erro de rede")

        # Não deve propagar a exceção
        await mandar_mensagem(mock_context, 123456, "Texto")

        # Verifica que a função completou sem erro
        assert True


class TestMandarImagemErrorHandling:
    """Testes para tratamento de erros em mandar_imagem()."""

    @pytest.mark.asyncio
    async def test_mandar_imagem_erro_arquivo_nao_encontrado(self, mock_context):
        # Tenta enviar imagem inexistente - não deve propagar erro
        with patch("interfaces.telegram.messaging.pathlib.Path.resolve", return_value="/tmp"):
            await mandar_imagem(mock_context, 123456, "arquivo_inexistente_12345")

        # A função não deve levantar exceção
        assert True
