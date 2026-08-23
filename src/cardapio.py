"""Lógica de transformação e formatação de cardápios.

Este módulo contém apenas lógica de transformação de dados e pode ser testado
independentemente de Firebase, Telegram ou qualquer outro serviço externo.
"""


from util import MODALIDADES

# Mapeamento de período para índices da lista de comida
PERIODOS_INDICES = {
    'Almoço': [0, 1],      # tradicional, vegano
    'Jantar': [2, 3],      # tradicional, vegano
}

NOMES_MODALIDADES = {
    (0, True): MODALIDADES[0],   # Almoço Tradicional
    (1, False): MODALIDADES[1],  # Almoço Vegano
    (2, True): MODALIDADES[2],   # Jantar Tradicional
    (3, False): MODALIDADES[3],  # Jantar Vegano
}


def modalidade_com_cardapio(comida: list, dados: dict, modalidade: str) -> list:
    """Retorna lista de (prato, nome_modalidade) para a modalidade solicitada.

    A lógica de filtragem é baseada nas preferências do usuário:
    - Se tradicional=1 e vegano=0: mostra apenas tradicional
    - Se tradicional=0 e vegano=1: mostra apenas vegano
    - Se tradicional=1 e vegano=1: mostra ambos
    - Se tradicional=0 e vegano=0: mostra ambos (padrão)

    Args:
        comida: Lista com 5 elementos [almoco_tradicional, almoco_vegano,
                jantar_tradicional, jantar_vegano, cafe].
        dados: Dicionário com preferências do usuário.
        modalidade: 'Almoço', 'Jantar' ou 'Café da manhã'.

    Returns:
        Lista de tuplas (prato, nome_modalidade) para a modalidade solicitada.
    """
    cardapio = []

    if modalidade == 'Café da manhã':
        if dados.get('cafe', 1):
            cardapio.append((comida[4], MODALIDADES[4]))

    elif modalidade in ('Almoço', 'Jantar'):
        indice_tradicional = PERIODOS_INDICES[modalidade][0]
        indice_vegano = PERIODOS_INDICES[modalidade][1]

        trad_enabled = dados.get('tradicional', 1) == 1
        veg_enabled = dados.get('vegano', 1) == 1

        # Se nenhum está explícito (0,0), mostra ambos como padrão
        if not trad_enabled and not veg_enabled:
            trad_enabled = True
            veg_enabled = True

        if trad_enabled:
            cardapio.append((comida[indice_tradicional], NOMES_MODALIDADES[(indice_tradicional, True)]))
        if veg_enabled:
            cardapio.append((comida[indice_vegano], NOMES_MODALIDADES[(indice_vegano, False)]))

    return cardapio


def formatar_cardapio_para_mensagem(cardapio: list, dia_semana: str) -> list:
    """Formata lista de cardápio em mensagens para envio.

    Args:
        cardapio: Lista de tuplas (prato, nome_modalidade).
        dia_semana: Nome do dia da semana (ex: 'Segunda-feira').

    Returns:
        Lista de strings formatadas para envio como mensagem.
    """
    mensagens = []
    for item, modalidade in cardapio:
        if item != 'Refeição não cadastrada.':
            msg = f'*{modalidade} de {dia_semana}* \n\n{item}'
            mensagens.append(msg)
    return mensagens
