from datetime import timedelta

import base64
import cv2
import datetime as dt
import json
import numpy as np
import pathlib
import urllib.request

from util import CAM_WEB, CAM_RU_A, CAM_RU_B, CAM_RA, CAM_RS, CAM_IS_JSON


def salvarImagem(imagens, cameras):
    for imagem, camera in zip(imagens, cameras):
        cv2.imwrite(f'{pathlib.Path().resolve()}/{camera}.jpg', imagem)


def verificarAtualizacao(atualizacao):
    data = dt.datetime.today() - timedelta(minutes=atualizacao.minute)
    return True if data.minute > 0 else False


class Cam:
    atualizacao_ru = dt.datetime.today() - timedelta(minutes=1)
    atualizacao_ra = dt.datetime.today() - timedelta(minutes=1)
    atualizacao_rs = dt.datetime.today() - timedelta(minutes=1)

    def pegarImagem(self, id):
        imagens = list()

        if id == 'ru':
            if not (verificarAtualizacao(self.atualizacao_ru)):
                return
            self.atualizacao_ru = dt.datetime.today()
            cameras = [CAM_RU_A, CAM_RU_B]

        elif id == 'ra':
            if not (verificarAtualizacao(self.atualizacao_ra)):
                return
            self.atualizacao_ra = dt.datetime.today()
            cameras = [CAM_RA]

        else:
            if not (verificarAtualizacao(self.atualizacao_rs)):
                return
            self.atualizacao_rs = dt.datetime.today()
            cameras = [CAM_RS]

        for camera in cameras:
            try:
                if CAM_IS_JSON:
                    resp = urllib.request.urlopen(CAM_WEB + camera + '.json')
                    resp = json.loads(resp.read().decode('utf-8'))
                    imagem = base64.b64decode(resp['image_jpg_b64'])
                    imagem = np.frombuffer(imagem, dtype="uint8")
                    imagem = cv2.imdecode(imagem, cv2.IMREAD_COLOR)
                else:
                    resp = urllib.request.urlopen(CAM_WEB + camera + '.jpg')
                    imagem = np.asarray(bytearray(resp.read()), dtype="uint8")
                    imagem = cv2.imdecode(imagem, cv2.IMREAD_COLOR)
            except:
                return

            imagens.append(imagem)

        salvarImagem(imagens, cameras)
