"""Agendador simples dentro do processo da API (sem dependência extra). Ligue com HABITUS_SCHEDULER=1.

Frequência (1 h) é suposição: os documentos citam "Cron Jobs" sem periodicidade. Em produção com vários
processos, prefira um cron do sistema chamando `python -m app.modules.automacoes` (evita rodar em duplicidade).
"""
import asyncio
import logging

from app.core.database import SessionLocal
from app.modules.automacoes.jobs import executar_todos

log = logging.getLogger("habitus.automacoes")


def _rodar_uma_vez() -> None:
    with SessionLocal() as db:
        executar_todos(db)


async def loop(intervalo_s: int = 3600) -> None:
    while True:
        try:
            await asyncio.to_thread(_rodar_uma_vez)
        except Exception:  # noqa: BLE001 — uma falha não pode derrubar o agendador
            log.exception("falha ao executar automações")
        await asyncio.sleep(intervalo_s)
