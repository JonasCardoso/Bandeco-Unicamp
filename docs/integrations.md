# Integrações

## Unicamp

Clientes de cardápio, horários, preços, saldo e câmeras definem timeout, retry e validação de status. Parsing inválido ou indisponibilidade retorna o fallback já esperado pelos módulos de negócio. Chamadas são executadas fora do event loop.

## Firebase

A URL vem de `DATABASE_URL_FIREBASE`. `FIREBASE_JSON` pode conter JSON ou caminho de arquivo. A inicialização é lazy/cacheada, mas é validada antes do polling. O schema de usuários não é alterado por esta arquitetura.

## Telegram

O token cria a aplicação de polling. Um error handler global registra exceções imprevistas. Falhas do próprio canal de logs vão apenas ao logger Python para evitar recursão.

## Meta

A integração exige Graph API `v26.0`, Page Access Token, ID da página e ID da conta profissional do Instagram. A sessão HTTP é fechada após o lote. Erros Meta são convertidos em mensagens sanitizadas com operação, status, código e trace ID quando disponíveis.

## Cloudflare R2

Imagens do Instagram são enviadas a um prefixo `social-media/AAAA-MM-DD/<uuid>`, recebem URL assinada de 15 minutos e são removidas no `finally`. O cliente é fechado após a limpeza.

## X/Twitter

O `tweetkit-x` usa `TWEETKIT_COOKIE`. Textos com “Observações:” viram thread. A postagem ocorre em thread de trabalho; uma falha invalida o cliente para que a próxima tentativa reconstrua a sessão.

## Política de erros

Timeout, rede, HTTP, autenticação e parsing são diferenciados nas fronteiras. Tokens, cookies, senhas e headers de autorização não devem aparecer em logs ou exceções destinadas ao canal.

