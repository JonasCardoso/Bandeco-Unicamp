from telegram import KeyboardButton
from util import verificar_atividade


def teclado_dias_semana(periodo, dias):
    return [[KeyboardButton(f'{periodo} de {dias[i]}')] for i in range(0, len(dias))]


def teclado_modalidades(dados):
    return ([[KeyboardButton(f"Tradicional - {verificar_atividade(dados, 'tradicional')}")],
             [KeyboardButton(f"Vegano - {verificar_atividade(dados, 'vegano')}")]])


def teclado_notificacao(dados):
    return ([[KeyboardButton(f"Café - {verificar_atividade(dados, 'cafe')}")],
             [KeyboardButton(f"Almoço - {verificar_atividade(dados, 'almoco')}")],
             [KeyboardButton(f"Jantar - {verificar_atividade(dados, 'jantar')}")]])


def teclado_contato():
    return [[KeyboardButton("Compartilhar meu contato", request_contact=True)]]
