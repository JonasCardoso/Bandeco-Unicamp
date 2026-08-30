"""Controle de atualização e persistência das imagens das câmeras."""

import datetime as dt
import logging
from datetime import timedelta
from pathlib import Path
from typing import List, Optional

from core.config import get_cam_ra, get_cam_rs, get_cam_ru_a, get_cam_ru_b
from integrations.unicamp.camera_client import fetch_camera

logger = logging.getLogger(__name__)


def salvar_imagem(imagens: list[bytes], cameras: List[str]) -> None:
    for imagem, camera in zip(imagens, cameras, strict=True):
        destino = Path.cwd() / f"{camera}.jpg"
        temporario = destino.with_suffix(".jpg.tmp")
        temporario.write_bytes(imagem)
        temporario.replace(destino)


def verificar_atualizacao(atualizacao, agora=None) -> bool:
    """Retorna se decorreu ao menos um minuto desde a última captura."""
    referencia = agora or dt.datetime.today()
    return referencia - atualizacao >= timedelta(minutes=1)


class Cam:
    """Gerencia o throttling e a captura das câmeras por restaurante."""

    def __init__(self):
        inicial = dt.datetime.today() - timedelta(minutes=1)
        self.atualizacao_ru = inicial
        self.atualizacao_ra = inicial
        self.atualizacao_rs = inicial

    def pegar_imagem(self, id_cam: str) -> Optional[list]:
        agora = dt.datetime.today()
        if id_cam == "ru":
            if not verificar_atualizacao(self.atualizacao_ru, agora):
                return None
            self.atualizacao_ru = agora
            cameras = [get_cam_ru_a(), get_cam_ru_b()]
        elif id_cam == "ra":
            if not verificar_atualizacao(self.atualizacao_ra, agora):
                return None
            self.atualizacao_ra = agora
            cameras = [get_cam_ra()]
        else:
            if not verificar_atualizacao(self.atualizacao_rs, agora):
                return None
            self.atualizacao_rs = agora
            cameras = [get_cam_rs()]

        try:
            imagens = [fetch_camera(camera) for camera in cameras]
        except Exception as erro:
            logger.warning("Falha ao capturar câmera %s: %s", id_cam, erro)
            return None
        salvar_imagem(imagens, cameras)
        return imagens
