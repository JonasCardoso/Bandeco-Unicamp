"""Testes do heartbeat usado pelo container."""

import asyncio
import os

from app.scheduler import schedule_jobs
from shared import health


class JobQueueFalsa:
    def __init__(self):
        self.repeating = []
        self.daily = []

    def run_repeating(self, callback, **kwargs):
        self.repeating.append((callback, kwargs))

    def run_daily(self, callback, horario, **kwargs):
        self.daily.append((callback, horario, kwargs))


class AplicacaoFalsa:
    def __init__(self):
        self.job_queue = JobQueueFalsa()


def test_healthcheck_exige_heartbeat_recente(tmp_path, monkeypatch):
    arquivo = tmp_path / "heartbeat"
    monkeypatch.setattr(health, "HEALTHCHECK_FILE", arquivo)
    assert not health.esta_saudavel()
    health.registrar_heartbeat()
    mtime = arquivo.stat().st_mtime
    assert health.esta_saudavel(mtime + health.HEALTHCHECK_MAX_AGE_SECONDS)
    assert not health.esta_saudavel(mtime + health.HEALTHCHECK_MAX_AGE_SECONDS + 1)


def test_callback_atualiza_heartbeat(tmp_path, monkeypatch):
    arquivo = tmp_path / "heartbeat"
    monkeypatch.setattr(health, "HEALTHCHECK_FILE", arquivo)
    asyncio.run(health.atualizar_heartbeat(None))
    assert arquivo.exists()


def test_scheduler_registra_heartbeat_e_refresco(tmp_path, monkeypatch):
    arquivo = tmp_path / "heartbeat"
    monkeypatch.setattr(health, "HEALTHCHECK_FILE", arquivo)
    monkeypatch.setattr("app.scheduler.registrar_heartbeat", health.registrar_heartbeat)
    aplicacao = AplicacaoFalsa()
    schedule_jobs(aplicacao, 7, 12, 19)
    assert arquivo.exists()
    assert len(aplicacao.job_queue.repeating) == 1
    _, opcoes = aplicacao.job_queue.repeating[0]
    assert opcoes == {"interval": 30, "first": 0, "name": "container-heartbeat"}
    assert len(aplicacao.job_queue.daily) == 3


def test_main_retorna_status_compativel(monkeypatch):
    monkeypatch.setattr(health, "esta_saudavel", lambda: True)
    try:
        health.main()
    except SystemExit as erro:
        assert erro.code == os.EX_OK
