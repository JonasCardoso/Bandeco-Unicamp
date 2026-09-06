"""Destaque de títulos sem interpretar o conteúdo como Markdown ou HTML."""

from telegram import MessageEntity


def titulo_em_negrito(texto: str, secoes=(), destacar_primeiro=True) -> list[MessageEntity]:
    entidades = []
    offset = 0
    for indice, linha in enumerate(texto.splitlines(keepends=True)):
        titulo = linha.rstrip("\r\n")
        if titulo and ((indice == 0 and destacar_primeiro) or titulo in secoes):
            entidades.append(MessageEntity(type="bold", offset=offset, length=len(titulo.encode("utf-16-le")) // 2))
        offset += len(linha.encode("utf-16-le")) // 2
    return entidades
