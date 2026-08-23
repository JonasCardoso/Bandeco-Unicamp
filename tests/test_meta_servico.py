"""Testes unitários para meta_servico.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from meta_servico import (
    criar_carrossel_instagram,
    criar_container_instagram,
    postar_meta,
    postar_timeline_facebook,
    postar_timeline_instagram,
)


class TestCriarContainerInstagram:
    """Testes para a função criar_container_instagram()."""

    def test_cria_container_com_sucesso(self):
        mock_log = MagicMock()
        with patch("meta_servico.req.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"id": "media_123456"}'
            mock_post.return_value = mock_response

            result = criar_container_instagram("img.jpg", True, "Caption", "http://url.com", mock_log)

            assert result == "media_123456"
            mock_post.assert_called_once()

    def test_cria_container_falha_retorna_false(self):
        mock_log = MagicMock()
        with patch("meta_servico.req.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = '{"error": "Server error"}'
            mock_post.return_value = mock_response

            result = criar_container_instagram("img.jpg", True, "Caption", "http://url.com", mock_log)

            assert result is False
            mock_log.adicionar_log.assert_called_once()


class TestCriarCarrosselInstagram:
    """Testes para a função criar_carrossel_instagram()."""

    def test_cria_carrossel_com_sucesso(self):
        mock_log = MagicMock()
        with patch("meta_servico.req.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"id": "carousel_789"}'
            mock_post.return_value = mock_response

            result = criar_carrossel_instagram(["media_1", "media_2"], "Caption", mock_log)

            assert result == "carousel_789"

    def test_cria_carrossel_falha_retorna_false(self):
        mock_log = MagicMock()
        with patch("meta_servico.req.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = '{"error": "Invalid request"}'
            mock_post.return_value = mock_response

            result = criar_carrossel_instagram(["media_1"], "Caption", mock_log)

            assert result is False


class TestPostarTimelineInstagram:
    """Testes para a função postar_timeline_instagram()."""

    def test_publica_na_timeline_com_sucesso(self):
        mock_log = MagicMock()
        with patch("meta_servico.req.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = postar_timeline_instagram("creation_123", "Caption", mock_log)

            assert result is True

    def test_publica_na_timeline_falha_retorna_false(self):
        mock_log = MagicMock()
        with patch("meta_servico.req.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_post.return_value = mock_response

            result = postar_timeline_instagram("creation_123", "Caption", mock_log)

            assert result is False


class TestPostarTimelineFacebook:
    """Testes para a função postar_timeline_facebook()."""

    def test_publica_no_facebook_com_sucesso(self):
        mock_log = MagicMock()
        with patch("meta_servico.req.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = postar_timeline_facebook("http://url.com", "img.jpg", "Caption", mock_log)

            assert result is True

    def test_publica_no_facebook_falha_retorna_false(self):
        mock_log = MagicMock()
        with patch("meta_servico.req.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_post.return_value = mock_response

            result = postar_timeline_facebook("http://url.com", "img.jpg", "Caption", mock_log)

            assert result is False


class TestPostarMetaIntegration:
    """Testes de integração para a função postar_meta()."""

    @pytest.mark.asyncio
    async def test_posta_meta_com_sucesso(self, mock_context):
        mock_log = MagicMock()
        with patch("meta_servico.gerar_imagem_postagem") as mock_gerar:
            with patch("meta_servico.postar_instagram", new_callable=AsyncMock) as mock_ig:
                with patch("meta_servico.postar_facebook", new_callable=AsyncMock) as mock_fb:
                    mock_gerar.return_value = ["img_cardapio_post_0.jpg"]
                    mock_ig.return_value = None
                    mock_fb.return_value = None

                    await postar_meta(mock_context, "Almoço Tradicional", "Frango grelhado\nArroz", mock_log, "http://url.com")

                    mock_gerar.assert_called_once()
                    mock_ig.assert_called_once()
                    mock_fb.assert_called_once()

    @pytest.mark.asyncio
    async def test_posta_meta_sem_imagem_retorna(self, mock_context):
        mock_log = MagicMock()
        with patch("meta_servico.gerar_imagem_postagem") as mock_gerar:
            with patch("meta_servico.postar_instagram", new_callable=AsyncMock) as mock_ig:
                with patch("meta_servico.postar_facebook", new_callable=AsyncMock) as mock_fb:
                    mock_gerar.return_value = None

                    await postar_meta(mock_context, "Almoço Tradicional", "Frango grelhado", mock_log, "http://url.com")

                    # Não deve tentar postar se não há imagem
                    mock_ig.assert_not_called()
                    mock_fb.assert_not_called()
