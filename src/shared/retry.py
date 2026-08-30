"""Retry síncrono e assíncrono com backoff exponencial."""

import asyncio
import inspect
import logging
import time
from functools import wraps
from typing import Callable, Tuple

logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[type[BaseException], ...] = (Exception,),
) -> Callable:
    """Repete funções síncronas ou assíncronas com backoff exponencial."""
    if max_attempts < 1:
        raise ValueError("max_attempts deve ser maior ou igual a 1")

    def decorator(func: Callable) -> Callable:
        def registrar_tentativa(attempt: int, erro: BaseException) -> None:
            espera = delay * (2**attempt)
            logger.warning(
                "%s falhou (tentativa %s/%s): %s; nova tentativa em %.1fs",
                func.__name__,
                attempt + 1,
                max_attempts,
                erro,
                espera,
            )

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as erro:
                        if attempt == max_attempts - 1:
                            logger.error("%s falhou após %s tentativas", func.__name__, max_attempts)
                            raise
                        registrar_tentativa(attempt, erro)
                        await asyncio.sleep(delay * (2**attempt))

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as erro:
                    if attempt == max_attempts - 1:
                        logger.error("%s falhou após %s tentativas", func.__name__, max_attempts)
                        raise
                    registrar_tentativa(attempt, erro)
                    time.sleep(delay * (2**attempt))

        return sync_wrapper

    return decorator
