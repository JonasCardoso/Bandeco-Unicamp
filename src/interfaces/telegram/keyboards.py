"""Geração de teclados interativos para o bot Telegram.

Este módulo fornece funções para criar teclados com botões para
dias da semana, modalidades de refeição e notificações.
"""

from telegram import KeyboardButton

from modules.preferences.rules import verificar_atividade


def teclado_dias_semana(periodo: str, dias: list) -> list:
    """Gera teclado com botões para dias da semana.

    Args:
        periodo: Nome do período (ex: 'Café', 'Almoço').
        dias: Lista de nomes dos dias.

    Returns:
        Estrutura de botões para ReplyKeyboardMarkup.
    """
    return [[KeyboardButton(f"{periodo} de {dias[i]}")] for i in range(0, len(dias))]


def teclado_modalidades(dados: dict) -> list:
    """Gera teclado com opções de modalidade (tradicional/vegano).

    Args:
        dados: Dicionário com preferências do usuário.

    Returns:
        Estrutura de botões para ReplyKeyboardMarkup.
    """
    return [
        [KeyboardButton(f"Tradicional - {verificar_atividade(dados, 'tradicional')}")],
        [KeyboardButton(f"Vegano - {verificar_atividade(dados, 'vegano')}")],
    ]


def teclado_notificacao(dados: dict) -> list:
    """Gera teclado com opções de notificação (café/almoço/jantar).

    Args:
        dados: Dicionário com preferências do usuário.

    Returns:
        Estrutura de botões para ReplyKeyboardMarkup.
    """
    return [
        [KeyboardButton(f"Café - {verificar_atividade(dados, 'cafe')}")],
        [KeyboardButton(f"Almoço - {verificar_atividade(dados, 'almoco')}")],
        [KeyboardButton(f"Jantar - {verificar_atividade(dados, 'jantar')}")],
    ]


def teclado_contato() -> list:
    """Gera teclado com botão para compartilhar contato.

    Returns:
        Estrutura de botões para ReplyKeyboardMarkup.
    """
    return [[KeyboardButton("Compartilhar meu contato", request_contact=True)]]
