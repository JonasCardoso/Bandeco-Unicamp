from datetime import timedelta

from telegram import Update, ForceReply
from telegram.ext import CallbackContext

import bandeco
import cam as cm
import datetime as dt
import log as lg
from horario import horarioFuncionamento
from saldo import saldoBandeco
from servico import modalidadeComCardapio, mensagemCardapioTelegram, firebase
from teclado import tecladoDiasSemana, tecladoModalidades, tecladoNotificacao, tecladoContato
from telegramServico import mandarMensagem, mandarImagem, mandarMensagemTeclado, deletarMensagem
from util import DIAS, CAM_RU_A, CAM_RU_B, CAM_RA, CAM_RS

log = lg.Log()
cam = cm.Cam()


def start(update: Update, context: CallbackContext):
    if firebase.criarUsuario(update.effective_chat.id):
        mandarMensagem(context, update.effective_chat.id, 'Olá Unicamper, seja bem-vindo ao Bandeco Unicamp, consulte '
                                                          'e receba os cardapio diários da universidade!!!')
        return
    else:
        mandarMensagem(context, update.effective_chat.id,
                       'Olá Unicamper, houve algum problema na base de dados, use /start novamente!!!')
        log.adicionarLog(f'start - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                         f'{update.effective_chat.username} - Não foi possível criar o usuário')
        log.enviarLog(context)


def cafe(update: Update, context: CallbackContext):
    periodo = 'Café da manhã'
    buttons = tecladoDiasSemana(periodo, DIAS)
    mandarMensagemTeclado(context, update.effective_chat.id, "Selecione o dia da semana", buttons)


def almoco(update: Update, context: CallbackContext):
    periodo = 'Almoço'
    buttons = tecladoDiasSemana(periodo, DIAS)
    mandarMensagemTeclado(context, update.effective_chat.id, "Selecione o dia da semana", buttons)


def jantar(update: Update, context: CallbackContext):
    periodo = 'Jantar'
    buttons = tecladoDiasSemana(periodo, DIAS)
    mandarMensagemTeclado(context, update.effective_chat.id, "Selecione o dia da semana", buttons)


def modalidade(update: Update, context: CallbackContext):
    dados = firebase.pegarUsuario(update.effective_chat.id)
    if dados:
        buttons = tecladoModalidades(dados)
        mandarMensagemTeclado(context, update.effective_chat.id, "Ative ou inative de acordo com sua preferência",
                              buttons)
        return

    log.adicionarLog(f'modalidade - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                     f'{update.effective_chat.username} - Não foi possível pegar o usuário')
    log.enviarLog(context)


def notificacao(update: Update, context: CallbackContext):
    dados = firebase.pegarUsuario(update.effective_chat.id)
    if dados:
        buttons = tecladoNotificacao(dados)
        mandarMensagemTeclado(context, update.effective_chat.id, "Ative ou inative de acordo com sua preferência",
                              buttons)
        return

    log.adicionarLog(f'notificacao - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                     f'{update.effective_chat.username} - Não foi possível pegar o usuário')
    log.enviarLog(context)


def saldo(update: Update, context: CallbackContext):
    mandarMensagem(context, update.effective_chat.id, 'Digite seu RA e a senha da DAC no formato "<RA> <Senha>" para '
                                                      'consultar seu saldo. Exemplo: 123456 abcdefghi',
                   forceReply=ForceReply())


def ru(update: Update, context: CallbackContext):
    cam.pegarImagem('ru')
    mandarImagem(context, update.effective_chat.id, CAM_RU_A)
    mandarImagem(context, update.effective_chat.id, CAM_RU_B)


def ra(update: Update, context: CallbackContext):
    cam.pegarImagem('ra')
    mandarImagem(context, update.effective_chat.id, CAM_RA)


def rs(update: Update, context: CallbackContext):
    cam.pegarImagem('rs')
    mandarImagem(context, update.effective_chat.id, CAM_RS)


def horario(update: Update, context: CallbackContext):
    horarios = horarioFuncionamento()
    if horario is None:
        log.adicionarLog(f'horario - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                         f'{update.effective_chat.username} - Não foi possível pegar o horario')
        log.enviarLog(context)
        return

    mandarMensagem(context, update.effective_chat.id, horarios)


def contato(update: Update, context: CallbackContext):
    buttons = tecladoContato()
    mandarMensagemTeclado(context, update.effective_chat.id,
                          "Compartilhe seu contato para ser notificado no WhatsApp",
                          buttons)


def twitter(update: Update, context: CallbackContext):
    mandarMensagem(context, update.effective_chat.id,
                   'Atualizações diárias no twitter: https://twitter.com/bandecounicamp')


def instagram(update: Update, context: CallbackContext):
    mandarMensagem(context, update.effective_chat.id,
                   'Atualizações diárias no instagram: https://instagram.com/bandecounicamp')


def desativar(update: Update, context: CallbackContext):
    dados = {"tradicional": 0, "vegano": 0, "cafe": 0, "almoco": 0, "jantar": 0, "telefone": 0}
    if firebase.atualizarUsuario(dados, update.effective_chat.id):
        mandarMensagem(context, update.effective_chat.id,
                       'Olá Unicamper, seus dados da modalidade, notificação e telefone foram zerados!!!')
        return

    log.adicionarLog(f'desativar - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                     f'{update.effective_chat.username} - Não foi possível zerar os dados do usuário')
    log.enviarLog(context)


def ajuda(update: Update, context: CallbackContext):
    texto = (
        '''Com Bandeco Unicamp você pode consultar com facilidade os cardápios do RU, RS e RA da Unicamp.

Além de receber notificações diárias das suas modalidades cadastradas.

Use o /cafe para consultar o cardápio do café da manhã.
Use o /almoco para consultar o cardápio do almoço.
Use o /jantar para consultar o cardápio do jantar.

Use o /modalidade para definir entre a modalidade de cardápio vegano e/ou tradicional.
Use o /notificacao para escolher quais cardápios serão notificados.
Use o /horario para saber o horário de funcionamento dos restaurantes.
Use o /saldo para consultar o saldo no cartão universitário.

Use o /ru para receber imagens das câmeras do RU.
Use o /ra para receber imagens das câmeras do RA.
Use o /rs para receber imagens das câmeras do RS.

Use o /twitter para receber o link da página do Twitter.
Use o /instagram para receber o link da página do Instagram.

Use o /desativar para zerar seus dados cadastrados no bot.

By @JonasCardoso''')
    mandarMensagem(context, update.effective_chat.id, texto)


def mensagemContato(update: Update, context: CallbackContext):
    dados = firebase.pegarUsuario(update.effective_chat.id)
    if dados:
        if update.message.contact['user_id'] == update.effective_chat.id:
            dados['telefone'] = str(update.message.contact['phone_number']).replace('+', '')
            if firebase.adicionarContato(dados, update.effective_chat.id):
                mandarMensagem(context, update.effective_chat.id, "Contato atualizado !")
            else:
                log.adicionarLog(f'mensagemContato - {update.effective_chat.id} - {update.effective_chat.full_name} -'
                                 f'{update.effective_chat.username} - Não foi possível atualizar o contato')
                log.enviarLog(context)
            return

    log.adicionarLog(f'mensagemContato - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                     f'{update.effective_chat.username} - Não foi possível pegar o usuário')
    log.enviarLog(context)


def mensagem(update: Update, context: CallbackContext):
    hoje = dt.datetime.today()

    if len(update.message.text.split('de')) > 1 and (update.message.text.split('de')[1].strip() in DIAS):
        dia = hoje - timedelta(days=hoje.weekday() - DIAS.index(update.message.text.split('de')[1].strip()))
        data = dia.strftime('%Y-%m-%d')
        comida = bandeco.comida(data)

        if comida is None:
            mandarMensagem(context, update.effective_chat.id, "Algo deu errado !")
            log.adicionarLog(f'{update.message.text} - {update.effective_chat.id} - {update.effective_chat.full_name} '
                             f'- {update.effective_chat.username} - Não foi possível consultar o cardápio')
            log.enviarLog(context)

        else:
            dados = firebase.pegarUsuario(update.effective_chat.id)
            if not dados:
                log.adicionarLog(f'mensagem - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                                 f'{update.effective_chat.username} - Não foi possível pegar o usuário')
                log.enviarLog(context)
                return

            periodo = update.message.text.split('de')[0].strip()
            cardapio = modalidadeComCardapio(comida, dados, periodo)
            mensagemCardapioTelegram(update.effective_chat.id, context, cardapio, dia)

    elif 'Ativo' in update.message.text or 'Inativo' in update.message.text:
        dados = firebase.pegarUsuario(update.effective_chat.id)
        if not dados:
            log.adicionarLog(f'mensagem - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                             f'{update.effective_chat.username} - Não foi possível pegar o usuário')
            log.enviarLog(context)
            return

        if 'Tradicional' in update.message.text:
            dados['tradicional'] = 0 if dados['tradicional'] else 1
        elif 'Vegano' in update.message.text:
            dados['vegano'] = 0 if dados['vegano'] else 1
        elif 'Café' in update.message.text:
            dados['cafe'] = 0 if dados['cafe'] else 1
        elif 'Almoço' in update.message.text:
            dados['almoco'] = 0 if dados['almoco'] else 1
        elif 'Jantar' in update.message.text:
            dados['jantar'] = 0 if dados['jantar'] else 1

        if not firebase.atualizarUsuario(dados, update.effective_chat.id):
            log.adicionarLog(f'mensagem - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                             f'{update.effective_chat.username} - Não foi possível atualizar o usuário')
            log.enviarLog(context)
            return

        if 'Tradicional' in update.message.text or 'Vegano' in update.message.text:
            modalidade(update, context)
        else:
            notificacao(update, context)

    elif len(update.message.text.split()) == 2 and update.message.text.split()[0].isnumeric():
        ra = update.message.text.split()[0]
        senha = update.message.text.split()[1]
        deletarMensagem(context, update.effective_chat.id, update.message.message_id)

        valor = saldoBandeco(context, update, ra, senha, log)
        if valor is not None:
            mandarMensagem(context, update.effective_chat.id, valor)
