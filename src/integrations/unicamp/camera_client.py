"""Cliente para captura de JPEGs das câmeras da Prefeitura."""

import base64
import binascii
import json
import urllib.request

from core.config import get_cam_is_json, get_cam_web


class CameraPayloadError(ValueError):
    """Indica que a câmera não devolveu um JPEG válido."""


def _validar_jpeg(conteudo: bytes) -> bytes:
    if len(conteudo) < 4 or not conteudo.startswith(b"\xff\xd8") or not conteudo.endswith(b"\xff\xd9"):
        raise CameraPayloadError("A câmera não retornou um JPEG válido.")
    return conteudo


def fetch_camera(camera: str) -> bytes:
    """Baixa uma câmera e retorna o JPEG original, sem recompressão."""
    sufixo = ".json" if get_cam_is_json() else ".jpg"
    with urllib.request.urlopen(get_cam_web() + camera + sufixo, timeout=10) as response:
        conteudo = response.read()
    if get_cam_is_json():
        try:
            payload = json.loads(conteudo.decode("utf-8"))
            conteudo = base64.b64decode(payload["image_jpg_b64"], validate=True)
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, binascii.Error) as erro:
            raise CameraPayloadError("Payload JSON/base64 inválido.") from erro
    return _validar_jpeg(conteudo)
