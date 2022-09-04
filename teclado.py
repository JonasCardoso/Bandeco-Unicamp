from telegram import KeyboardButton
from util import verificarAtividade


def tecladoDiasSemana(periodo, DIAS):
    return [[KeyboardButton(f'{periodo} de {DIAS[i]}')] for i in range(0, 5)]


def tecladoModalidades(dados):
    return ([[KeyboardButton(f"Tradicional - {verificarAtividade(dados, 'tradicional')}")],
             [KeyboardButton(f"Vegano - {verificarAtividade(dados, 'vegano')}")]])


def tecladoNotificacao(dados):
    return ([[KeyboardButton(f"Café - {verificarAtividade(dados, 'cafe')}")],
             [KeyboardButton(f"Almoço - {verificarAtividade(dados, 'almoco')}")],
             [KeyboardButton(f"Jantar - {verificarAtividade(dados, 'jantar')}")]])


def tecladoContato():
    return [[KeyboardButton("Compartilhar meu contato", request_contact=True)]]
