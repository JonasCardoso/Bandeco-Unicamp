"""Ajuda compartilhada entre o comando e o painel do Telegram."""

AJUDA = """Bandeco Unicamp — como usar

/menu abre o painel com cardápios, câmeras, horários, preços, saldo e preferências.
/start inicia o cadastro ou reabre o painel, preservando suas escolhas. No primeiro cadastro, você escolhe quais notificações receber.

CARDÁPIOS E NUTRIÇÃO
/cafe, /almoco e /jantar mostram o cardápio de hoje. Nos botões, escolha Hoje, Amanhã ou Escolher dia e alterne tradicional/vegano sem mudar suas notificações.
Toque em Ver nutrição no cardápio ou use /tabela respondendo à mensagem do cardápio. A geração pode levar alguns instantes; os valores são estimativas não oficiais.

NOTIFICAÇÕES
/modalidade e /notificacao abrem suas preferências: modalidades, refeições, dias da semana, envio silencioso e pausa. Pausar preserva suas escolhas para retomar depois. Os horários de envio seguem a programação do bot.

CONSULTAS
/horario mostra os horários dos restaurantes; /preco, os valores das refeições.
/ru, /ra e /rs mostram as câmeras. Pelo painel, você também pode escolher o restaurante e atualizar as imagens, que podem estar em cache.
/saldo inicia uma consulta no privado: informe RA e senha em até cinco minutos. Use /cancelar para encerrar ou /menu para voltar.

CADASTRO E DADOS
/contato permite cadastrar seu próprio telefone opcionalmente; não há envio automático por WhatsApp.
/reset_contato remove o telefone.
/reset_modalidade zera as preferências de modalidade.
/reset_notificacao desativa as notificações de refeições.
/desativar zera modalidades, refeições e telefone, mantendo o cadastro.
/excluir remove o cadastro e o registro de entregas após sua confirmação. Não apaga mensagens já recebidas no Telegram.

REDES SOCIAIS
/twitter, /instagram e /facebook mostram os links das páginas.

Use Voltar e Início para navegar pelos botões.
Desenvolvido por @JonasCardoso"""


SECOES_AJUDA = (
    "CARDÁPIOS E NUTRIÇÃO",
    "NOTIFICAÇÕES",
    "CONSULTAS",
    "CADASTRO E DADOS",
    "REDES SOCIAIS",
)
