"""Cliente para captura de uma imagem das câmeras da Prefeitura."""

import base64
import json
import urllib.request

import cv2
import numpy as np

from core.config import get_cam_is_json, get_cam_web


def fetch_camera(camera: str):
    """Baixa e decodifica uma imagem de câmera."""
    if get_cam_is_json():
        response = urllib.request.urlopen(get_cam_web() + camera + ".json", timeout=10)
        payload = json.loads(response.read().decode("utf-8"))
        raw = base64.b64decode(payload["image_jpg_b64"])
        encoded = np.frombuffer(raw, dtype="uint8")
    else:
        response = urllib.request.urlopen(get_cam_web() + camera + ".jpg", timeout=10)
        encoded = np.asarray(bytearray(response.read()), dtype="uint8")
    return cv2.imdecode(encoded, cv2.IMREAD_COLOR)
