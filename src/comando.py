from datetime import timedelta

from telegram import Update, ForceReply
from telegram.ext import CallbackContext

import bandeco
import cam as cm
import datetime as dt
import log as lg
from horario import horario_funcionamento
from saldo import saldo_bandeco
from servico import modalidade_com_cardapio, mensagem_cardapio_telegram, firebase
from teclado import teclado_dias_semana, teclado_modalidades, teclado_notificacao, teclado_contato
from telegram_servico import mandar_mensagem, mandar_imagem, mandar_mensagem_teclado, deletar_mensagem
from util import DIAS, CAM_RU_A, CAM_RU_B, CAM_RA, CAM_RS

log = lg.Log()
cam = cm.Cam()


async def start(update: Update, context: CallbackContext):
    if firebase.criar_usuario(update.effective_chat.id):
        await mandar_mensagem(context, update.effective_chat.id,
                              'Olá Unicamper, seja bem-vindo ao Bandeco Unicamp, consulte '
                              'e receba os cardápios diários da universidade!!!')
        return
    else:
        await mandar_mensagem(context, update.effective_chat.id,
                              'Olá Unicamper, houve algum problema na base de dados, use /start novamente!!!')
        log.adicionar_log(f'start - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                          f'{update.effective_chat.username} - Não foi possível criar o usuário')
        await log.enviar_log(context)


async def cafe(update: Update, context: CallbackContext):
    periodo = 'Café da manhã'
    buttons = teclado_dias_semana(periodo, DIAS)
    await mandar_mensagem_teclado(context, update.effective_chat.id, "Selecione o dia da semana", buttons)


async def almoco(update: Update, context: CallbackContext):
    periodo = 'Almoço'
    buttons = teclado_dias_semana(periodo, DIAS)
    await mandar_mensagem_teclado(context, update.effective_chat.id, "Selecione o dia da semana", buttons)


async def jantar(update: Update, context: CallbackContext):
    periodo = 'Jantar'
    buttons = teclado_dias_semana(periodo, DIAS)
    await mandar_mensagem_teclado(context, update.effective_chat.id, "Selecione o dia da semana", buttons)


async def modalidade(update: Update, context: CallbackContext):
    dados = firebase.pegar_usuario(update.effective_chat.id)
    if dados:
        buttons = teclado_modalidades(dados)
        await mandar_mensagem_teclado(context, update.effective_chat.id,
                                      "Ative ou inative de acordo com sua preferência",
                                      buttons)
        return

    log.adicionar_log(f'modalidade - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                      f'{update.effective_chat.username} - Não foi possível pegar o usuário')
    await log.enviar_log(context)


async def notificacao(update: Update, context: CallbackContext):
    dados = firebase.pegar_usuario(update.effective_chat.id)
    if dados:
        buttons = teclado_notificacao(dados)
        await mandar_mensagem_teclado(context, update.effective_chat.id,
                                      "Ative ou inative de acordo com sua preferência",
                                      buttons)
        return

    log.adicionar_log(f'notificacao - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                      f'{update.effective_chat.username} - Não foi possível pegar o usuário')
    await log.enviar_log(context)


async def saldo(update: Update, context: CallbackContext):
    await mandar_mensagem(context, update.effective_chat.id,
                          'Digite seu RA e a senha da DAC no formato "<RA> <Senha>" para '
                          'consultar seu saldo. Exemplo: 123456 abcdefghi',
                          reply_markup=ForceReply())


async def ru(update: Update, context: CallbackContext):
    cam.pegar_imagem('ru')
    await mandar_imagem(context, update.effective_chat.id, CAM_RU_A)
    await mandar_imagem(context, update.effective_chat.id, CAM_RU_B)


async def ra(update: Update, context: CallbackContext):
    cam.pegar_imagem('ra')
    await mandar_imagem(context, update.effective_chat.id, CAM_RA)


async def rs(update: Update, context: CallbackContext):
    cam.pegar_imagem('rs')
    await mandar_imagem(context, update.effective_chat.id, CAM_RS)


async def horario(update: Update, context: CallbackContext):
    horarios = horario_funcionamento()
    if horario is None:
        log.adicionar_log(f'horario - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                          f'{update.effective_chat.username} - Não foi possível pegar o horario')
        await log.enviar_log(context)
        return

    await mandar_mensagem(context, update.effective_chat.id, horarios)


async def contato(update: Update, context: CallbackContext):
    buttons = teclado_contato()
    await mandar_mensagem_teclado(context, update.effective_chat.id,
                                  "Compartilhe seu contato para ser notificado no WhatsApp",
                                  buttons)


async def twitter(update: Update, context: CallbackContext):
    await mandar_mensagem(context, update.effective_chat.id,
                          'Atualizações diárias no twitter: https://x.com/bandecounicamp')


async def instagram(update: Update, context: CallbackContext):
    await mandar_mensagem(context, update.effective_chat.id,
                          'Atualizações diárias no instagram: https://instagram.com/bandecounicamp')


async def facebook(update: Update, context: CallbackContext):
    await mandar_mensagem(context, update.effective_chat.id,
                          'Atualizações diárias no facebook: https://facebook.com/bandecounicamp')


async def desativar(update: Update, context: CallbackContext):
    dados = {"tradicional": 0, "vegano": 0, "cafe": 0, "almoco": 0, "jantar": 0, "telefone": 0}
    if firebase.atualizar_usuario(dados, update.effective_chat.id):
        await mandar_mensagem(context, update.effective_chat.id,
                              'Olá Unicamper, seus dados da modalidade, notificação e telefone foram zerados!!!')
        return

    log.adicionar_log(f'desativar - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                      f'{update.effective_chat.username} - Não foi possível zerar os dados do usuário')
    await log.enviar_log(context)


async def ajuda(update: Update, context: CallbackContext):
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
Use o /facebook para receber o link da página do Facebook.

Use o /desativar para zerar seus dados cadastrados no bot.

By @JonasCardoso''')
    await mandar_mensagem(context, update.effective_chat.id, texto)


async def mensagem_contato(update: Update, context: CallbackContext):
    dados = firebase.pegar_usuario(update.effective_chat.id)
    if dados:
        if update.message.contact['user_id'] == update.effective_chat.id:
            dados['telefone'] = str(update.message.contact['phone_number']).replace('+', '')
            if firebase.adicionar_contato(dados, update.effective_chat.id):
                await mandar_mensagem(context, update.effective_chat.id, "Contato atualizado !")
            else:
                log.adicionar_log(f'mensagemContato - {update.effective_chat.id} - {update.effective_chat.full_name} -'
                                  f'{update.effective_chat.username} - Não foi possível atualizar o contato')
                await log.enviar_log(context)
            return

    log.adicionar_log(f'mensagemContato - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                      f'{update.effective_chat.username} - Não foi possível pegar o usuário')
    await log.enviar_log(context)


async def mensagem(update: Update, context: CallbackContext):
    hoje = dt.datetime.today()

    if len(update.message.text.split('de')) > 1 and (update.message.text.split('de')[1].strip() in DIAS):
        dia = hoje - timedelta(days=hoje.weekday() - DIAS.index(update.message.text.split('de')[1].strip()))
        data = dia.strftime('%Y-%m-%d')
        comida = bandeco.comida(data)

        if comida is None:
            await mandar_mensagem(context, update.effective_chat.id, "Algo deu errado !")
            log.adicionar_log(f'{update.message.text} - {update.effective_chat.id} - {update.effective_chat.full_name} '
                              f'- {update.effective_chat.username} - Não foi possível consultar o cardápio')
            await log.enviar_log(context)

        else:
            dados = firebase.pegar_usuario(update.effective_chat.id)
            if not dados:
                log.adicionar_log(f'mensagem - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                                  f'{update.effective_chat.username} - Não foi possível pegar o usuário')
                await log.enviar_log(context)
                return

            periodo = update.message.text.split('de')[0].strip()
            cardapio = modalidade_com_cardapio(comida, dados, periodo)
            await mensagem_cardapio_telegram(update.effective_chat.id, context, cardapio, dia)

    elif 'Ativo' in update.message.text or 'Inativo' in update.message.text:
        dados = firebase.pegar_usuario(update.effective_chat.id)
        if not dados:
            log.adicionar_log(f'mensagem - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                              f'{update.effective_chat.username} - Não foi possível pegar o usuário')
            await log.enviar_log(context)
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

        if not firebase.atualizar_usuario(dados, update.effective_chat.id):
            log.adicionar_log(f'mensagem - {update.effective_chat.id} - {update.effective_chat.full_name} - '
                              f'{update.effective_chat.username} - Não foi possível atualizar o usuário')
            await log.enviar_log(context)
            return

        if 'Tradicional' in update.message.text or 'Vegano' in update.message.text:
            await modalidade(update, context)
        else:
            await notificacao(update, context)

    elif len(update.message.text.split()) == 2 and update.message.text.split()[0].isnumeric():
        ra_numero = update.message.text.split()[0]
        senha = update.message.text.split()[1]
        await deletar_mensagem(context, update.effective_chat.id, update.message.message_id)

        valor = await saldo_bandeco(update, context, ra_numero, senha, log)
        if valor is not None:
            await mandar_mensagem(context, update.effective_chat.id, valor)
