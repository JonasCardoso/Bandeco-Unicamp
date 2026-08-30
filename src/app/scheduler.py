"""Agendamento dos envios automáticos de cardápio."""

import datetime as dt
from zoneinfo import ZoneInfo

from modules.notifications.service import notificar_cardapio
from shared.health import atualizar_heartbeat, registrar_heartbeat

FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")
DIAS_DA_SEMANA = tuple(range(7))


def schedule_jobs(application, cafe_hour: int, lunch_hour: int, dinner_hour: int) -> None:
    """Registra os três jobs diários no job queue do Telegram."""
    registrar_heartbeat()
    application.job_queue.run_repeating(
        atualizar_heartbeat,
        interval=30,
        first=0,
        name="container-heartbeat",
    )
    jobs = (
        ("Café da manhã", cafe_hour),
        ("Almoço", lunch_hour),
        ("Jantar", dinner_hour),
    )
    for nome, hora in jobs:
        application.job_queue.run_daily(
            notificar_cardapio,
            dt.time(hour=hora, minute=0, tzinfo=FUSO_HORARIO),
            days=DIAS_DA_SEMANA,
            name=nome,
        )
