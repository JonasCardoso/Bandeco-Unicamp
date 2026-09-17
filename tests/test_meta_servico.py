"""Testes da publicação Meta Graph API v26."""

import json
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from integrations.social import meta
from integrations.social.meta import MetaAPIError, MetaClient


def resposta(payload, status=200):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = payload
    return response


def cliente(session, **kwargs):
    return MetaClient(
        access_token="segredo-meta",
        instagram_user_id="ig-1",
        facebook_page_id="page-1",
        api_version="v26.0",
        session=session,
        **kwargs,
    )


class TestInstagram:
    def test_publica_imagem_unica_na_v26_com_bearer(self):
        session = MagicMock()
        session.post.side_effect = [resposta({"id": "container-1"}), resposta({"id": "media-1"})]
        session.get.return_value = resposta({"status_code": "FINISHED"})

        resultado = cliente(session).publicar_instagram(["https://storage/imagem.jpg?assinatura=x"], "Legenda")

        assert resultado == "media-1"
        primeira = session.post.call_args_list[0]
        assert primeira.args[0] == "https://graph.facebook.com/v26.0/ig-1/media"
        assert primeira.kwargs["headers"] == {"Authorization": "Bearer segredo-meta"}
        assert primeira.kwargs["data"]["caption"] == "Legenda"
        assert "access_token" not in primeira.kwargs["data"]
        assert primeira.kwargs["timeout"] == (5, 30)

    def test_publica_duas_imagens_como_carrossel(self):
        session = MagicMock()
        session.post.side_effect = [
            resposta({"id": "child-1"}),
            resposta({"id": "child-2"}),
            resposta({"id": "carousel-1"}),
            resposta({"id": "media-1"}),
        ]
        session.get.side_effect = [
            resposta({"status_code": "FINISHED"}),
            resposta({"status_code": "FINISHED"}),
            resposta({"status_code": "FINISHED"}),
        ]

        resultado = cliente(session).publicar_instagram(["https://storage/a.jpg", "https://storage/b.jpg"], "Menu")

        assert resultado == "media-1"
        primeiro_filho = session.post.call_args_list[0].kwargs["data"]
        assert primeiro_filho == {"image_url": "https://storage/a.jpg", "is_carousel_item": "true"}
        pai = session.post.call_args_list[2].kwargs["data"]
        assert pai == {"media_type": "CAROUSEL", "children": "child-1,child-2", "caption": "Menu"}

    def test_aguarda_container_em_processamento(self):
        session = MagicMock()
        session.get.side_effect = [
            resposta({"status_code": "IN_PROGRESS"}),
            resposta({"status_code": "FINISHED"}),
        ]
        esperas = []
        relogio = iter([0, 0, 1])
        client = cliente(session, sleep=esperas.append, monotonic=lambda: next(relogio))

        client._aguardar_container_instagram("container")

        assert esperas == [60]

    def test_container_com_erro_falha_sem_publicar(self):
        session = MagicMock()
        session.post.return_value = resposta({"id": "container-1"})
        session.get.return_value = resposta({"status_code": "ERROR"})

        with pytest.raises(MetaAPIError, match="container error"):
            cliente(session).publicar_instagram(["https://storage/a.jpg"], "Menu")
        assert session.post.call_count == 1

    @pytest.mark.parametrize("status", ["ERROR", "EXPIRED"])
    def test_status_terminal_falha_sem_nova_consulta(self, status):
        session = MagicMock()
        session.get.return_value = resposta({"status_code": status})

        with pytest.raises(MetaAPIError, match=f"container {status.lower()}"):
            cliente(session)._aguardar_container_instagram("container")
        session.get.assert_called_once()

    def test_timeout_do_container_apos_cinco_minutos(self):
        session = MagicMock()
        session.get.return_value = resposta({"status_code": "IN_PROGRESS"})
        relogio = iter([0, 300])
        esperas = []

        with pytest.raises(MetaAPIError, match="timeout do container"):
            cliente(
                session,
                sleep=esperas.append,
                monotonic=lambda: next(relogio),
            )._aguardar_container_instagram("container")

        assert esperas == []


class TestFacebook:
    def test_publica_uma_imagem_pelo_mesmo_fluxo(self, tmp_path):
        caminho = tmp_path / "cardapio.jpg"
        caminho.write_bytes(b"jpeg")
        session = MagicMock()
        session.post.side_effect = [resposta({"id": "photo-1"}), resposta({"id": "post-1"})]

        assert cliente(session).publicar_facebook([caminho], "Menu") == "post-1"
        feed = session.post.call_args_list[1].kwargs["data"]
        assert json.loads(feed["attached_media"]) == [{"media_fbid": "photo-1"}]

    def test_publica_carrossel_com_upload_multipart(self, tmp_path):
        caminhos = [tmp_path / "a.jpg", tmp_path / "b.jpg"]
        for caminho in caminhos:
            caminho.write_bytes(b"jpeg")
        session = MagicMock()
        session.post.side_effect = [
            resposta({"id": "photo-1"}),
            resposta({"id": "photo-2"}),
            resposta({"id": "post-1"}),
        ]

        resultado = cliente(session).publicar_facebook(caminhos, "Menu")

        assert resultado == "post-1"
        upload = session.post.call_args_list[0]
        assert upload.args[0] == "https://graph.facebook.com/v26.0/page-1/photos"
        assert upload.kwargs["data"] == {"published": "false"}
        assert upload.kwargs["files"]["source"][2] == "image/jpeg"
        feed = session.post.call_args_list[2]
        assert feed.args[0].endswith("/page-1/feed")
        assert json.loads(feed.kwargs["data"]["attached_media"]) == [
            {"media_fbid": "photo-1"},
            {"media_fbid": "photo-2"},
        ]

    def test_upload_parcial_nao_cria_post(self, tmp_path):
        caminhos = [tmp_path / "a.jpg", tmp_path / "b.jpg"]
        for caminho in caminhos:
            caminho.write_bytes(b"jpeg")
        session = MagicMock()
        session.post.side_effect = [
            resposta({"id": "photo-1"}),
            resposta({"error": {"code": 200, "type": "OAuthException"}}, 403),
        ]

        with pytest.raises(MetaAPIError):
            cliente(session).publicar_facebook(caminhos, "Menu")
        assert session.post.call_count == 2


class TestErros:
    def test_cliente_rejeita_versao_diferente(self):
        session = MagicMock()

        with pytest.raises(ValueError, match="somente a Graph API v26.0"):
            MetaClient(
                access_token="token",
                instagram_user_id="ig-1",
                facebook_page_id="page-1",
                api_version="v25.0",
                session=session,
            )
        session.post.assert_not_called()

    def test_erro_graph_e_sanitizado(self):
        session = MagicMock()
        session.post.return_value = resposta(
            {"error": {"message": "segredo-meta", "code": 190, "type": "OAuthException", "fbtrace_id": "trace-1"}},
            401,
        )

        with pytest.raises(MetaAPIError) as capturado:
            cliente(session).publicar_instagram(["https://storage/a.jpg"], "Menu")

        detalhe = capturado.value.sanitized()
        assert "segredo-meta" not in detalhe
        assert "http=401" in detalhe
        assert "code=190" in detalhe
        assert "trace=trace-1" in detalhe


class TestOrquestracao:
    def test_falha_instagram_nao_impede_facebook(self, tmp_path, monkeypatch):
        client = MagicMock()
        client.publicar_instagram.side_effect = MetaAPIError("instagram.publish", status=500)
        monkeypatch.setattr(meta, "_novo_cliente", lambda: client)

        def gerar(_titulo, _texto, _log, diretorio):
            caminho = diretorio / "menu.jpg"
            caminho.write_bytes(b"jpeg")
            return [caminho]

        @contextmanager
        def hospedar(_caminhos):
            yield ["https://storage/menu.jpg"]

        monkeypatch.setattr(meta, "gerar_imagem_postagem", gerar)
        monkeypatch.setattr(meta, "hospedar_imagens", hospedar)
        log = MagicMock()

        meta._postar_meta_sync("Menu", "Arroz", log)

        client.publicar_facebook.assert_called_once()
        assert "segredo" not in str(log.adicionar_log.call_args_list)

    @pytest.mark.asyncio
    async def test_wrapper_async_usa_thread(self, mock_context, monkeypatch):
        chamadas = []

        async def to_thread(func, *args):
            chamadas.append((func, args))

        monkeypatch.setattr(meta.asyncio, "to_thread", to_thread)
        log = MagicMock()
        await meta.postar_meta(mock_context, "Menu", "Arroz", log)
        assert chamadas == [(meta._postar_meta_sync, ("Menu", "Arroz", log))]


def test_cliente_fecha_sessao_criada_internamente(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(meta.requests, "Session", lambda: session)
    client = MetaClient(
        access_token="segredo-meta",
        instagram_user_id="ig-1",
        facebook_page_id="page-1",
        api_version="v26.0",
    )

    client.close()

    session.close.assert_called_once()
