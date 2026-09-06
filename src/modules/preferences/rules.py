"""Regras puras para preferências de usuário."""


def verificar_atividade(dados: dict, campo: str) -> str:
    """Retorna a apresentação do estado de uma preferência."""
    return "Inativo" if not dados[campo] else "Ativo"


def dias_ativos(dados: dict) -> tuple[int, ...]:
    """Máscara persistível inclusive sem dias; aceita listas de versões anteriores."""
    valor = dados.get("dias", 127)
    if isinstance(valor, (list, tuple)):
        return tuple(dia for dia in range(7) if dia in valor)
    if not isinstance(valor, int) or not 0 <= valor <= 127:
        valor = 127
    return tuple(dia for dia in range(7) if valor & (1 << dia))


def definir_dia(dados: dict, dia: int, ativo: bool) -> dict:
    if dia not in range(7):
        raise ValueError("Dia inválido")
    dias = set(dias_ativos(dados))
    dias.add(dia) if ativo else dias.discard(dia)
    return {**dados, "dias": sum(1 << item for item in dias)}


def deve_notificar(dados: dict, refeicao: str, dia: int) -> bool:
    return (
        bool(dados)
        and not dados.get("pausado", False)
        and not dados.get("bloqueado", False)
        and (dados.get(refeicao, 0) == 1 and dia in dias_ativos(dados))
    )
