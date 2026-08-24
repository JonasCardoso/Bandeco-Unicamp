"""Funções de validação de entrada sem dependências externas.

Este módulo contém apenas funções puras de validação e pode ser testado
independentemente de Firebase, Telegram ou qualquer outro serviço externo.
"""


def validar_saldo_entrada(ra: str, senha: str) -> bool:
    """Valida os dados de entrada para consulta de saldo.

    Args:
        ra: Número do RA (deve ser numérico).
        senha: Senha do RA (não deve conter espaços).

    Returns:
        True se válido, False caso contrário.
    """
    # RA deve ser apenas numérico e ter tamanho razoável
    if not ra.isdigit() or len(ra) < 3 or len(ra) > 15:
        return False

    # Senha não deve conter espaços (o espaço é usado como separador)
    if " " in senha or "\t" in senha:
        return False

    # Senha deve ter tamanho mínimo
    if len(senha) < 3:
        return False

    return True
