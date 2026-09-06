"""Trabalho nutricional compartilhado com concorrência limitada por aplicação."""

import asyncio
import hashlib
import logging

logger = logging.getLogger(__name__)


class NutritionJobs:
    def __init__(self):
        self.semaforo = asyncio.Semaphore(1)
        self.pendentes = {}

    async def gerar(self, texto, gerador):
        chave = hashlib.sha256(texto.encode()).hexdigest()
        tarefa = self.pendentes.get(chave)
        if tarefa is None:
            if len(self.pendentes) >= 8:
                return None

            async def executar():
                async with self.semaforo:
                    return await asyncio.to_thread(gerador, texto)

            tarefa = asyncio.create_task(executar())
            self.pendentes[chave] = tarefa

            def finalizar(t):
                self.pendentes.pop(chave, None)
                if not t.cancelled():
                    t.exception()

            tarefa.add_done_callback(finalizar)
        else:
            logger.info("nutrition_job_reused")
        return await asyncio.shield(tarefa)
