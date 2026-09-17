"""Divisão conservadora de mensagens sem perder caracteres Unicode."""


def fragmentos(texto: str, limite: int = 4000) -> list[str]:
    partes = []
    atual = []
    tamanho = 0
    for caractere in texto:
        unidades = 2 if ord(caractere) > 0xFFFF else 1
        if tamanho + unidades > limite:
            partes.append("".join(atual))
            atual, tamanho = [], 0
        atual.append(caractere)
        tamanho += unidades
    if atual:
        partes.append("".join(atual))
    return partes or [""]
