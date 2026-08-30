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

        mock_response = {"ok": True, "id": "1234567890"}

        with patch("integrations.social.twitter._get_client") as mock_get_client:
            mock_client_instance = MagicMock()
            mock_client_instance.post.return_value = mock_response
            mock_get_client.return_value = mock_client_instance

            await postar_tweet(mock_context, "Almoço", "Frango grelhado\nArroz", mock_log)

            mock_client_instance.post.assert_called_once_with("Almoço\n\nFrango grelhado\nArroz")
            mock_log.enviar_log.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_posta_tweet_com_observacoes_divide_em_dois(self, mock_context):
        from integrations.social.twitter import postar_tweet

        mock_log = MagicMock()
        mock_log.enviar_log = AsyncMock()

        call_count = [0]

        def mock_post(*args, **kwargs):
            call_count[0] += 1
            return {"ok": True, "id": f"tweet_{call_count[0]}"}

        with patch("integrations.social.twitter._get_client") as mock_get_client:
            mock_client_instance = MagicMock()
            mock_client_instance.post.side_effect = mock_post
            mock_get_client.return_value = mock_client_instance

            texto_com_obs = "Frango grelhado\nObservações: Contém glúten"
            await postar_tweet(mock_context, "Almoço", texto_com_obs, mock_log)

            assert mock_client_instance.post.call_count == 2
            assert mock_client_instance.post.call_args_list[0].args == ("Almoço\n\nFrango grelhado\n",)
            assert mock_client_instance.post.call_args_list[1].args == (" Contém glúten",)
            assert mock_client_instance.post.call_args_list[1].kwargs == {"reply_to": "tweet_1"}

    @pytest.mark.asyncio
    async def test_posta_tweet_erro_nao_propaga(self, mock_context):
        from integrations.social.twitter import postar_tweet

        mock_log = MagicMock()
        mock_log.enviar_log = AsyncMock()

        with patch("integrations.social.twitter._get_client") as mock_get_client:
            mock_client_instance = MagicMock()
            mock_client_instance.post.side_effect = Exception("Erro na API do Twitter")
            mock_get_client.return_value = mock_client_instance

            # Não deve levantar exceção
            await postar_tweet(mock_context, "Almoço", "Frango grelhado", mock_log)

            # Verifica que o log foi registrado
            assert mock_log.adicionar_log.called
            assert mock_log.enviar_log.called

    @pytest.mark.asyncio
    async def test_resposta_de_falha_e_enviada_ao_log(self, mock_context):
        from integrations.social.twitter import postar_tweet

        mock_log = MagicMock()
        mock_log.enviar_log = AsyncMock()

        with patch("integrations.social.twitter._get_client") as mock_get_client:
            mock_client_instance = MagicMock()
            mock_client_instance.post.return_value = {"ok": False, "error": "cookie expirado"}
            mock_get_client.return_value = mock_client_instance

            await postar_tweet(mock_context, "Almoço", "Frango grelhado", mock_log)

            assert "cookie expirado" in mock_log.adicionar_log.call_args.args[0]
            mock_log.enviar_log.assert_awaited_once_with(mock_context)


class TestTwitterServiceIntegration:
    """Testes de integracao para integrations.social.twitter."""

    def test_modulo_tem_funcoes_esperadas(self):
        from integrations.social import twitter as twitter_servico

        assert hasattr(twitter_servico, "_get_client")
        assert hasattr(twitter_servico, "postar_tweet")
