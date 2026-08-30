"""Regressões da captura e expiração das câmeras."""

import datetime as dt

from modules.cameras.service import verificar_atualizacao


def test_atualizacao_antes_de_um_minuto():
    agora = dt.datetime(2026, 8, 29, 20, 0, 30)
    assert not verificar_atualizacao(agora - dt.timedelta(seconds=59), agora)


def test_atualizacao_depois_de_um_minuto():
    agora = dt.datetime(2026, 8, 29, 20, 0, 30)
    assert verificar_atualizacao(agora - dt.timedelta(seconds=60), agora)


def test_atualizacao_na_virada_da_hora():
    anterior = dt.datetime(2026, 8, 29, 19, 59, 0)
    agora = dt.datetime(2026, 8, 29, 20, 0, 0)
    assert verificar_atualizacao(anterior, agora)
