"""Regras puras para preferências de usuário."""


def verificar_atividade(dados: dict, campo: str) -> str:
    """Retorna a apresentação do estado de uma preferência."""
    return "Inativo" if not dados[campo] else "Ativo"
