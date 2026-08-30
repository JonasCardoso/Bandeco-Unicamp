"""Publicação de cardápios no Instagram e Facebook pela Graph API v26."""

from __future__ import annotations

import asyncio
import json
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import closing
from pathlib import Path
from typing import Any

import requests
from telegram.ext import CallbackContext

from core.config import (
    get_facebook_page_id,
    get_instagram_user_id,
    get_meta_graph_api_version,
    get_meta_page_access_token,
)
from integrations.cloudflare.r2_storage import MediaStorageError, hospedar_imagens
from presentation.menu_images import gerar_imagem_postagem

REQUEST_TIMEOUT = (5, 30)
CONTAINER_POLL_INTERVAL_SECONDS = 60
CONTAINER_TIMEOUT_SECONDS = 300


class MetaAPIError(RuntimeError):
    """Erro sanitizado retornado pela Graph API ou pela camada HTTP."""

    def __init__(
        self,
        operation: str,
        *,
        status: int | None = None,
        code: int | None = None,
        error_type: str | None = None,
        trace_id: str | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(reason or "Falha na Graph API")
        self.operation = operation
        self.status = status
        self.code = code
        self.error_type = error_type
        self.trace_id = trace_id
        self.reason = reason

    def sanitized(self) -> str:
        campos = [f"operação={self.operation}"]
        if self.status is not None:
            campos.append(f"http={self.status}")
        if self.code is not None:
            campos.append(f"code={self.code}")
        if self.error_type:
            campos.append(f"type={self.error_type}")
        if self.trace_id:
            campos.append(f"trace={self.trace_id}")
        if self.reason:
            campos.append(f"motivo={self.reason}")
        return "; ".join(campos)


def _json_mapping(response: requests.Response) -> Mapping[str, Any]:
    try:
        dados = response.json()
    except requests.exceptions.JSONDecodeError:
        return {}
    return dados if isinstance(dados, Mapping) else {}


def _validar_resposta(response: requests.Response, operation: str) -> Mapping[str, Any]:
    dados = _json_mapping(response)
    if 200 <= response.status_code < 300:
        return dados
    erro = dados.get("error")
    erro = erro if isinstance(erro, Mapping) else {}
    raise MetaAPIError(
        operation,
        status=response.status_code,
        code=erro.get("code") if isinstance(erro.get("code"), int) else None,
        error_type=str(erro["type"]) if erro.get("type") else None,
        trace_id=str(erro["fbtrace_id"]) if erro.get("fbtrace_id") else None,
    )


class MetaClient:
    """Cliente síncrono e injetável para os endpoints de publicação Meta."""

    def __init__(
        self,
        *,
        access_token: str,
        instagram_user_id: str,
        facebook_page_id: str,
        api_version: str,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if api_version != "v26.0":
            raise ValueError("A integração Meta aceita somente a Graph API v26.0.")
        self.instagram_user_id = instagram_user_id
        self.facebook_page_id = facebook_page_id
        self.base_url = f"https://graph.facebook.com/{api_version}"
        self._owns_session = session is None
        self.session = session if session is not None else requests.Session()
        self.headers = {"Authorization": f"Bearer {access_token}"}
        self.sleep = sleep
        self.monotonic = monotonic

    def close(self) -> None:
        """Fecha apenas a sessão criada internamente pelo cliente."""
        if self._owns_session:
            self.session.close()

    def _post(
        self,
        path: str,
        operation: str,
        *,
        data: Mapping[str, Any] | None = None,
        files: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        try:
            response = self.session.post(
                f"{self.base_url}/{path.lstrip('/')}",
                headers=self.headers,
                data=data,
                files=files,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as erro:
            raise MetaAPIError(operation, reason="falha de rede") from erro
        return _validar_resposta(response, operation)

    def _get(self, path: str, operation: str, *, params: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            response = self.session.get(
                f"{self.base_url}/{path.lstrip('/')}",
                headers=self.headers,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as erro:
            raise MetaAPIError(operation, reason="falha de rede") from erro
        return _validar_resposta(response, operation)

    @staticmethod
    def _id(dados: Mapping[str, Any], operation: str) -> str:
        identificador = dados.get("id")
        if not isinstance(identificador, str) or not identificador:
            raise MetaAPIError(operation, reason="resposta sem id")
        return identificador

    def _criar_imagem_instagram(self, image_url: str, *, carousel_item: bool, caption: str | None) -> str:
        payload: dict[str, Any] = {"image_url": image_url}
        if carousel_item:
            payload["is_carousel_item"] = "true"
        if caption:
            payload["caption"] = caption
        dados = self._post(f"{self.instagram_user_id}/media", "instagram.create_image", data=payload)
        return self._id(dados, "instagram.create_image")

    def _criar_carrossel_instagram(self, children: Sequence[str], caption: str) -> str:
        dados = self._post(
            f"{self.instagram_user_id}/media",
            "instagram.create_carousel",
            data={"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption},
        )
        return self._id(dados, "instagram.create_carousel")

    def _aguardar_container_instagram(self, container_id: str) -> None:
        limite = self.monotonic() + CONTAINER_TIMEOUT_SECONDS
        while True:
            dados = self._get(
                container_id,
                "instagram.container_status",
                params={"fields": "status_code,status"},
            )
            status = str(dados.get("status_code", "")).upper()
            if status in {"FINISHED", "PUBLISHED"}:
                return
            if status in {"ERROR", "EXPIRED"}:
                raise MetaAPIError("instagram.container_status", reason=f"container {status.lower()}")
            if self.monotonic() >= limite:
                raise MetaAPIError("instagram.container_status", reason="timeout do container")
            self.sleep(CONTAINER_POLL_INTERVAL_SECONDS)

    def publicar_instagram(self, image_urls: Sequence[str], caption: str) -> str:
        if not 1 <= len(image_urls) <= 10:
            raise ValueError("O Instagram aceita de 1 a 10 imagens por publicação.")
        if len(image_urls) == 1:
            container = self._criar_imagem_instagram(image_urls[0], carousel_item=False, caption=caption)
        else:
            children = [self._criar_imagem_instagram(url, carousel_item=True, caption=None) for url in image_urls]
            for child in children:
                self._aguardar_container_instagram(child)
            container = self._criar_carrossel_instagram(children, caption)
        self._aguardar_container_instagram(container)
        dados = self._post(
            f"{self.instagram_user_id}/media_publish",
            "instagram.publish",
            data={"creation_id": container},
        )
        return self._id(dados, "instagram.publish")

    def _enviar_foto_facebook(self, caminho: Path) -> str:
        with caminho.open("rb") as arquivo:
            dados = self._post(
                f"{self.facebook_page_id}/photos",
                "facebook.upload_photo",
                data={"published": "false"},
                files={"source": (caminho.name, arquivo, "image/jpeg")},
            )
        return self._id(dados, "facebook.upload_photo")

    def publicar_facebook(self, caminhos: Sequence[Path], message: str) -> str:
        if not caminhos:
            raise ValueError("Ao menos uma imagem é necessária para publicar no Facebook.")
        photo_ids = [self._enviar_foto_facebook(caminho) for caminho in caminhos]
        attached_media = [{"media_fbid": photo_id} for photo_id in photo_ids]
        payload = {"message": message, "attached_media": json.dumps(attached_media)}
        dados = self._post(f"{self.facebook_page_id}/feed", "facebook.publish", data=payload)
        return self._id(dados, "facebook.publish")


def _novo_cliente() -> MetaClient:
    return MetaClient(
        access_token=get_meta_page_access_token(),
        instagram_user_id=get_instagram_user_id(),
        facebook_page_id=get_facebook_page_id(),
        api_version=get_meta_graph_api_version(),
    )


def _registrar_falha(log, plataforma: str, erro: BaseException) -> None:
    if isinstance(erro, MetaAPIError):
        detalhe = erro.sanitized()
    elif isinstance(erro, MediaStorageError):
        detalhe = "falha ao hospedar mídia temporária"
    elif isinstance(erro, ValueError):
        detalhe = str(erro)
    else:
        detalhe = type(erro).__name__
    log.error(detalhe, component=f"meta.{plataforma}", event="publish_failed")


def _postar_meta_sync(titulo: str, texto: str, log) -> None:
    try:
        cliente = _novo_cliente()
    except ValueError as erro:
        _registrar_falha(log, "config", erro)
        return

    with closing(cliente), tempfile.TemporaryDirectory(prefix="bandeco-meta-") as diretorio:
        imagens = gerar_imagem_postagem(titulo, texto, log, Path(diretorio))
        if not imagens:
            return
        caminhos = [Path(imagem) for imagem in imagens]

        try:
            with hospedar_imagens(caminhos) as urls:
                cliente.publicar_instagram(urls, titulo)
        except (MediaStorageError, MetaAPIError, ValueError) as erro:
            _registrar_falha(log, "instagram", erro)

        try:
            cliente.publicar_facebook(caminhos, titulo)
        except (MetaAPIError, OSError, ValueError) as erro:
            _registrar_falha(log, "facebook", erro)


async def postar_meta(context: CallbackContext, titulo: str, texto: str, log) -> None:
    """Gera as imagens e publica nas duas plataformas sem bloquear o event loop."""
    del context
    await asyncio.to_thread(_postar_meta_sync, titulo, texto, log)
