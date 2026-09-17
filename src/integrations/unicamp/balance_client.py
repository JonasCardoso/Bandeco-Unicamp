"""Cliente HTTP para consulta de saldo do cartão universitário."""

import requests

from shared.retry import retry


@retry(max_attempts=3, delay=1.0, exceptions=(requests.RequestException,))
def _post_saldo(url: str, data: dict):
    response = requests.post(url, timeout=5, data=data)
    response.raise_for_status()
    return response
