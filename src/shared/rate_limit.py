"""Rate limiting simples em memória."""

import threading
import time


class RateLimiter:
    """Limita chamadas por chave dentro de uma janela deslizante."""

    def __init__(self, max_calls: int = 5, window_seconds: float = 60.0):
        self._max_calls = max_calls
        self._window_seconds = window_seconds
        self._calls: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            cutoff = now - self._window_seconds
            chamadas = [instante for instante in self._calls.get(key, []) if instante > cutoff]
            if len(chamadas) >= self._max_calls:
                self._calls[key] = chamadas
                return False
            chamadas.append(now)
            self._calls[key] = chamadas
            return True


rate_limiter_cardapio = RateLimiter(max_calls=15, window_seconds=60.0)
rate_limiter_saldo = RateLimiter(max_calls=5, window_seconds=60.0)
