"""Testes unitarios para integrations.social.twitter.py (integracao com Twitter/X)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGetClient:
    """Testes para a funcao _get_client()."""

    def test_retorna_instancia_do_cliente(self):
        from integrations.social import twitter

        # Garante que o client global e resetado
        original_client = twitter._client
        twitter._client = None

        try:
            result = twitter._get_client()
            assert result is not None
        finally:
            twitter._client = original_client


class TestPostarTweet:
    """Testes para a funcao postar_tweet()."""

    @pytest.mark.asyncio
    async def test_posta_tweet_com_sucesso(self, mock_context):
        from integrations.social.twitter import postar_tweet

        mock_log = MagicMock()
        mock_log.enviar_log = AsyncMock()

        # tweepy retorna lista de dicts com 'id'
        mock_response = [{"id": "1234567890"}]

        with patch("integrations.social.twitter._get_client") as mock_get_client:
            mock_client_instance = MagicMock()
            mock_client_instance.create_tweet.return_value = mock_response
            mock_get_client.return_value = mock_client_instance

            await postar_tweet(mock_context, "Almoço", "Frango grelhado\nArroz", mock_log)

            mock_client_instance.create_tweet.assert_called_once()

    @pytest.mark.asyncio
    async def test_posta_tweet_com_observacoes_divide_em_dois(self, mock_context):
        from integrations.social.twitter import postar_tweet

        mock_log = MagicMock()
        mock_log.enviar_log = AsyncMock()

        call_count = [0]

        def mock_create_tweet(*args, **kwargs):
            call_count[0] += 1
            # tweepy retorna lista de dicts com 'id'
            return [{"id": f"tweet_{call_count[0]}"}]

        with patch("integrations.social.twitter._get_client") as mock_get_client:
            mock_client_instance = MagicMock()
            mock_client_instance.create_tweet.side_effect = mock_create_tweet
            mock_get_client.return_value = mock_client_instance

            texto_com_obs = "Frango grelhado\nObservações: Contém glúten"
            await postar_tweet(mock_context, "Almoço", texto_com_obs, mock_log)

            # Deve chamar create_tweet duas vezes (cardápio + observações)
            assert mock_client_instance.create_tweet.call_count == 2

    @pytest.mark.asyncio
    async def test_posta_tweet_erro_nao_propaga(self, mock_context):
        from integrations.social.twitter import postar_tweet

        mock_log = MagicMock()
        mock_log.enviar_log = AsyncMock()

        with patch("integrations.social.twitter._get_client") as mock_get_client:
            mock_client_instance = MagicMock()
            mock_client_instance.create_tweet.side_effect = Exception("Erro na API do Twitter")
            mock_get_client.return_value = mock_client_instance

            # Não deve levantar exceção
            await postar_tweet(mock_context, "Almoço", "Frango grelhado", mock_log)

            # Verifica que o log foi registrado
            assert mock_log.adicionar_log.called
            assert mock_log.enviar_log.called


class TestTwitterServiceIntegration:
    """Testes de integracao para integrations.social.twitter."""

    def test_modulo_tem_funcoes_esperadas(self):
        from integrations.social import twitter as twitter_servico

        assert hasattr(twitter_servico, "_get_client")
        assert hasattr(twitter_servico, "postar_tweet")
