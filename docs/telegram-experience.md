# Experiência nativa do Telegram

## Fluxos

`/start` cria o usuário por transação apenas quando ausente. Novos cadastros começam sem notificações e escolhem modalidade e refeições. Repetições preservam as escolhas. `/menu` abre consultas em um toque; `/cafe`, `/almoco` e `/jantar` abrem hoje. A modalidade da consulta não modifica a assinatura. Os teclados de texto antigos continuam reconhecidos.

O painel usa mensagens editáveis. Um clique recebe confirmação imediata; mensagens removidas são substituídas por uma nova tela. Datas são explícitas e calculadas em America/Sao_Paulo. A seleção oferece hoje e os seis dias seguintes. Consultas de datas vindas de links/callbacks são limitadas a 366 dias em torno de hoje.

`/modalidade` e `/notificacao` abrem preferências inline. As refeições são ativadas ao selecionar seus botões. “Concluir” encerra o cadastro; “Agora não” não ativa notificações. Pausa preserva refeições, modalidades e dias. Usuários anteriores mantêm suas escolhas e, sem campos novos, recebem em todos os dias e com som.

`/saldo` funciona no privado e abre uma janela de cinco minutos para RA e senha. `/cancelar` encerra a janela. A credencial não é persistida; a mensagem é removida antes da consulta, quando o Telegram permite. O bot não considera qualquer mensagem numérica uma tentativa de autenticação.

`/desativar` zera as modalidades, refeições e telefone. `/excluir` pede confirmação com validade de cinco minutos e remove cadastro e registro de entregas em uma atualização atômica. Isso não remove o histórico de mensagens já armazenado no Telegram. `/contato` é opcional, destinado somente ao cadastro; não oferece notificações por WhatsApp.

A nutrição pode ser pedida pelo botão ou por `/tabela` respondendo ao cardápio. O atendimento acompanha a tarefa sem aguardar seu término no handler. Há uma execução nutricional por vez, até oito conteúdos distintos pendentes e uma solicitação por usuário. Pedidos simultâneos do mesmo conteúdo compartilham processamento. Texto e JPEG continuam disponíveis; o modelo e as imagens anteriores foram preservados.

## Callbacks e links

Callbacks UTF-8 têm até 64 bytes, prefixo `v1:` e parâmetros validados no servidor. São aceitos somente no privado do usuário que clicou.

| Formato | Efeito |
| --- | --- |
| `v1:home`, `v1:prefs`, `v1:cams`, `v1:info`, `v1:help` | Navegação |
| `v1:meal:almoco:2026-09-06:vegano` | Consulta sem alterar assinatura |
| `v1:dates:jantar:2026-09-06:tradicional` | Escolha de data |
| `v1:nutrition:almoco:2026-09-06:vegano` | Nutrição em tarefa acompanhada |
| `v1:set:almoco:1` | Define valor explícito; repetir não inverte o estado |
| `v1:day:0:0` | Desmarca segunda-feira |
| `v1:onboard:ambos`, `v1:skip`, `v1:done` | Cadastro; callbacks antigos não reinicializam cadastros concluídos |
| `v1:delete`, `v1:delete_confirm` | Exclusão com confirmação temporária |
| `v1:cam:ru`, `v1:hours`, `v1:prices`, `v1:saldo` | Consultas auxiliares |

Links de publicações usam `?start=cardapio_<refeicao>_<AAAA-MM-DD>_<modalidade>` e `?start=preferencias`. Eles abrem o privado; não editam mensagens do canal. Os nomes de refeição são `cafe`, `almoco`, `jantar`; modalidades são `tradicional`, `vegano`. Café mantém a opção única fornecida pela integração existente.

## Persistência e entrega

`/usuarios/<chat_id>` mantém os campos existentes e acrescenta:

- `cadastro_concluido`: ausente equivale a verdadeiro para preservar usuários antigos.
- `pausado`, `silencioso`, `bloqueado`: ausentes equivalem a falso.
- `dias`: máscara de sete bits, segunda-feira no bit zero; ausente equivale a 127. Zero representa nenhum dia. Listas antigas também são aceitas na leitura. A máscara evita que uma lista vazia desapareça no Realtime Database.

`/entregas/<destinatario>/<data>_<refeicao>_<modalidade>` registra estado, horário e identificação da mensagem confirmada. Mensagens longas têm sufixo por fragmento, para retomar sem repetir partes confirmadas. A reserva usa transação e token de posse. Estados confirmados, incertos e bloqueados não são reenviados automaticamente. Uma reserva abandonada por mais de dez minutos vira incerta na próxima tentativa. `RetryAfter` tem até três tentativas; esperas superiores a sessenta segundos ficam registradas como limite. Erros de rede/timeout são incertos, pois a mensagem pode ter sido aceita. Não há garantia de entrega exatamente uma vez.

O registro de deduplicação cobre Telegram. Meta e X permanecem com os fluxos de publicação existentes e informam sucesso/falha à rotina. Cada integração progride independentemente. A lista de usuários é relida individualmente antes do envio para respeitar mudanças recentes. Mensagens já enviadas ou em trânsito não podem ser recolhidas por uma pausa.

O job leva `refeicao` em seus dados e usa a data local de execução. Jobs que atravessam a meia-noite não devem ser reproduzidos como uma entrega retroativa: para reprocessamento histórico, usar uma operação explícita com data. O healthcheck mantém o heartbeat e arquivos adjacentes por rotina com início, fim e resultado. Logs registram duração das consultas, estados de disponibilidade e reaproveitamento nutricional; credenciais não são usadas como rótulos.

## Piloto visual

`TELEGRAM_RICH_ENABLED=false` é o padrão. Para teste isolado, habilitar e preencher `TELEGRAM_RICH_CHAT_IDS` com os IDs permitidos separados por vírgula. Sem ID permitido, nenhuma mensagem estruturada é usada.

O adaptador usa `Bot.do_api_request` para a Bot API posterior ao suporte nativo da biblioteca. Cardápios usam HTML escapado; nutrição oferece tabela recolhível e mantém o JPEG. Erros da API retornam à apresentação convencional. Botões desabilitados são apenas apresentação: callbacks continuam validados no servidor.

Referências: [Bot API](https://core.telegram.org/bots/api#inputrichmessage), [compatibilidade futura do PTB](https://github.com/python-telegram-bot/python-telegram-bot/wiki/Bot-API-Forward-Compatibility).

## Validação e liberação

Executar a suíte em `tests/`, lint, formatação e verificação de ciclos. As integrações externas são simuladas; testes não enviam ao canal operacional nem alteram Firebase real.

Antes de habilitar o piloto, validar em bot e chats de teste: Android, iOS e Desktop; tabelas longas e caracteres especiais; blocos recolhíveis; navegação após edição; retorno convencional quando recurso não está disponível. A validação automatizada não comprova a apresentação visual de clientes reais. Manter o piloto desligado até completar essa etapa.

Rollback visual: desativar a flag. Os campos Firebase são aditivos e a apresentação convencional permanece operacional. Mini App, modo inline, mensagens efêmeras e modo convidado ficam fora desta entrega.

## Ambiente de desenvolvimento

Os requisitos diretos foram conferidos no índice de pacotes. O ambiente `.venv` usa PyTorch CPU, como o Docker. Em WSL com checkout em disco Windows, a `.venv` pode ser um link para um ambiente no sistema de arquivos Linux para evitar lentidão de instalação. Ative com `source .venv/bin/activate`. O Python global não precisa ser modificado.
