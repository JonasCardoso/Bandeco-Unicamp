"""Testes do transporte JPEG das câmeras, sem OpenCV."""

import base64
import io
import json

import pytest

from integrations.unicamp import camera_client
from modules.cameras.service import salvar_imagem

JPEG = b"\xff\xd8conteudo\xff\xd9"


class Resposta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def configurar(monkeypatch, conteudo: bytes, json_ativo: bool):
    monkeypatch.setattr(camera_client, "get_cam_is_json", lambda: json_ativo)
    monkeypatch.setattr(camera_client, "get_cam_web", lambda: "https://camera/")
    monkeypatch.setattr(camera_client.urllib.request, "urlopen", lambda *_args, **_kwargs: Resposta(conteudo))


def test_fetch_camera_preserva_jpeg_direto(monkeypatch):
    configurar(monkeypatch, JPEG, False)
    assert camera_client.fetch_camera("ru") == JPEG


def test_fetch_camera_decodifica_json_base64(monkeypatch):
    payload = json.dumps({"image_jpg_b64": base64.b64encode(JPEG).decode()}).encode()
    configurar(monkeypatch, payload, True)
    assert camera_client.fetch_camera("ru") == JPEG


@pytest.mark.parametrize("conteudo,json_ativo", [(b"html", False), (b"{}", True), (b'{"image_jpg_b64":"!"}', True)])
def test_fetch_camera_rejeita_payload_invalido(monkeypatch, conteudo, json_ativo):
    configurar(monkeypatch, conteudo, json_ativo)
    with pytest.raises(camera_client.CameraPayloadError):
        camera_client.fetch_camera("ru")


def test_salvar_imagem_publica_atomicamente(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    salvar_imagem([JPEG], ["ru-a"])
    assert (tmp_path / "ru-a.jpg").read_bytes() == JPEG
    assert not (tmp_path / "ru-a.jpg.tmp").exists()


def test_fetch_camera_propaga_timeout(monkeypatch):
    monkeypatch.setattr(camera_client, "get_cam_is_json", lambda: False)
    monkeypatch.setattr(camera_client, "get_cam_web", lambda: "https://camera/")

    def timeout(*_args, **_kwargs):
        raise TimeoutError("tempo esgotado")

    monkeypatch.setattr(camera_client.urllib.request, "urlopen", timeout)
    with pytest.raises(TimeoutError):
        camera_client.fetch_camera("ru")
