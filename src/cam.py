"""Captura de imagens das câmeras dos restaurantes.

Este módulo fornece funções para capturar e salvar imagens
das câmeras instaladas nos restaurantes universitários.
"""

import base64
import datetime as dt
import json
import pathlib
import urllib.request
from datetime import timedelta
from typing import List, Optional

import cv2
import numpy as np

from util import get_cam_is_json, get_cam_ra, get_cam_rs, get_cam_ru_a, get_cam_ru_b, get_cam_web


def salvar_imagem(imagens: List[bytes], cameras: List[str]) -> None:
    """Salva imagens capturadas em arquivos JPG.

    Args:
        imagens: Lista de arrays numpy contendo as imagens.
        cameras: Lista de nomes das câmeras (usados como nomes de arquivo).
    """
    for imagem, camera in zip(imagens, cameras, strict=True):
        cv2.imwrite(f'{pathlib.Path().resolve()}/{camera}.jpg', imagem)


def verificar_atualizacao(atualizacao) -> bool:
    """Verifica se passou tempo suficiente para uma nova atualização.

    Args:
        atualizacao: Última data/hora de atualização.

    Returns:
        True se deve atualizar, False caso contrário.
    """
    data = dt.datetime.today() - timedelta(minutes=atualizacao.minute)
    return True if data.minute > 0 else False


class Cam:
    """Gerenciador de câmeras dos restaurantes.

    Attributes:
        atualizacao_ru: Última atualização das câmeras do RU.
        atualizacao_ra: Última atualização da câmera do RA.
        atualizacao_rs: Última atualização da câmera do RS.
    """

    atualizacao_ru = None  # type: ignore
    atualizacao_ra = None  # type: ignore
    atualizacao_rs = None  # type: ignore

    def __init__(self):
        """Inicializa o gerenciador de câmeras com timestamps iniciais."""
        self.atualizacao_ru = dt.datetime.today() - timedelta(minutes=1)
        self.atualizacao_ra = dt.datetime.today() - timedelta(minutes=1)
        self.atualizacao_rs = dt.datetime.today() - timedelta(minutes=1)

    def pegar_imagem(self, id_cam: str) -> Optional[List[bytes]]:
        """Captura imagens de uma câmera específica.

        Args:
            id_cam: Identificador da câmera ('ru', 'ra' ou 'rs').

        Returns:
            Lista de arrays numpy com as imagens ou None em caso de erro.
        """
        imagens = list()

        if id_cam == 'ru':
            if not verificar_atualizacao(self.atualizacao_ru):
                return
            self.atualizacao_ru = dt.datetime.today()
            cameras = [get_cam_ru_a(), get_cam_ru_b()]

        elif id_cam == 'ra':
            if not verificar_atualizacao(self.atualizacao_ra):
                return
            self.atualizacao_ra = dt.datetime.today()
            cameras = [get_cam_ra()]

        else:
            if not verificar_atualizacao(self.atualizacao_rs):
                return
            self.atualizacao_rs = dt.datetime.today()
            cameras = [get_cam_rs()]

        for camera in cameras:
            try:
                if get_cam_is_json():
                    resp = urllib.request.urlopen(get_cam_web() + camera + '.json')
                    resp = json.loads(resp.read().decode('utf-8'))
                    imagem = base64.b64decode(resp['image_jpg_b64'])
                    imagem = np.frombuffer(imagem, dtype="uint8")
                    imagem = cv2.imdecode(imagem, cv2.IMREAD_COLOR)
                else:
                    resp = urllib.request.urlopen(get_cam_web() + camera + '.jpg')
                    imagem = np.asarray(bytearray(resp.read()), dtype="uint8")
                    imagem = cv2.imdecode(imagem, cv2.IMREAD_COLOR)
            except Exception as e:
                print(f"[ERROR] Cam - pegar_imagem({id_cam}): {e}")
                return None

            imagens.append(imagem)

        salvar_imagem(imagens, cameras)
