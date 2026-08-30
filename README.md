# Bandeco Unicamp Bot

## Descrição

Bot do Telegram que reúne cardápios dos restaurantes universitários da Unicamp, horários, preços, saldo do cartão, câmeras e estimativas nutricionais. Também publica cardápios no Facebook, Instagram e X/Twitter quando essas integrações estão configuradas.

## Funcionalidades

- Consulta de café da manhã, almoço e jantar, com modalidades tradicional e vegana.
- Preferências e notificações diárias por usuário.
- Consulta de horários, preços, saldo e câmeras dos restaurantes.
- Imagem de tabela nutricional estimada com referências TACO/TBCA.
- Publicação programada no Telegram, Facebook, Instagram e X/Twitter.
- Healthcheck, cache persistente e canal de diagnóstico com logs sanitizados.

As estimativas nutricionais não substituem orientação profissional.

## Arquitetura

O entrypoint é `python -m app`. O bootstrap valida configuração, inicializa Firebase, constrói o bot, registra handlers/jobs e inicia o polling. Operações HTTP, SDKs e modelos síncronos são deslocados para threads nas fronteiras assíncronas.

- `app/`: bootstrap, scheduler e registro dos handlers.
- `core/`: configuração tipada e constantes.
- `interfaces/telegram/`: comandos, mensagens, teclados e logging.
- `modules/`: regras de negócio de cardápio, saldo, câmeras, notificações e nutrição.
- `integrations/`: Unicamp, Firebase, Meta, R2 e X/Twitter.
- `presentation/`: imagens e recursos gráficos.
- `shared/`: retry, rate limit e healthcheck.
- `tests/`: testes unitários e de integração com mocks.

Detalhes: [arquitetura](docs/architecture.md).

## Requisitos

- Python 3.12.
- Docker com Compose v2, caso a execução seja em container.
- Credenciais Telegram e Firebase.
- Memória e disco suficientes para PyTorch e modelos nutricionais quando `/tabela` for utilizado.

## Instalação

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

No PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
$env:PYTHONPATH = "src"
```

## Configuração

A aplicação lê `.env` na raiz. Nunca versione esse arquivo. `FIREBASE_JSON` aceita o JSON da conta de serviço ou um caminho para o arquivo montado.

## Variáveis de ambiente

| Grupo | Variáveis | Obrigatoriedade |
|---|---|---|
| Telegram | `TOKEN_BOT_TELEGRAM`, `USERNAME_BOT_TELEGRAM`, `ID_LOG_CHANNEL` | Obrigatórias |
| Firebase | `DATABASE_URL_FIREBASE`, `FIREBASE_JSON` | URL obrigatória; credencial necessária no startup |
| Agenda | `HORARIO_CAFE`, `HORARIO_ALMOCO`, `HORARIO_JANTAR` | Defaults no exemplo |
| Unicamp | `URL_BANDECO_PREFEITURA`, `URL_BANDECO_JSON`, `URL_HORARIO`, `URL_SALDO`, URLs de preços e câmeras | Defaults públicos |
| Meta | `META_PAGE_ACCESS_TOKEN`, `META_GRAPH_API_VERSION`, `FACEBOOK_PAGE_ID`, `INSTAGRAM_USER_ID` | Necessárias somente para publicação Meta |
| R2 | `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET` | Necessárias para mídia do Instagram |
| X/Twitter | `TWEETKIT_COOKIE` | Necessária somente para publicação no X |
| Modelos | `HF_TOKEN`, `HF_HOME` | Opcionais |
| Operação | `LOG_LEVEL`, `TELEGRAM_LOG_LEVEL`, `HEALTHCHECK_FILE` | Opcionais, com defaults |

Use somente `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL` nos níveis de log.

## Execução local

Na raiz do projeto:

```bash
PYTHONPATH=src python -m app
```

O pipeline nutricional é lazy: modelos são carregados na primeira solicitação e liberados após o período de inatividade. A primeira execução pode baixar modelos.

## Docker

```bash
cp .env.example .env
docker compose config --quiet
docker build --check .
docker build -t bandeco-unicamp:local .
docker compose up -d
```

A imagem roda como usuário não-root, inicia com `python -m app` e usa `/bandeco/.cache_bandeco_nutricao` como volume persistente. O healthcheck lê o heartbeat gravado pelo scheduler.

Para a imagem de desenvolvimento:

```bash
docker compose -f docker-compose.develop.yaml config --quiet
docker compose -f docker-compose.develop.yaml up -d
```

## Testes

```bash
python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=65
ruff check src tests tools
ruff format --check src tests tools
python tools/check_import_cycles.py
```

Os testes unitários usam mocks e não chamam Telegram, Firebase, Meta, R2, X ou Unicamp reais.

## Integrações externas

### Telegram

Recebe comandos, envia notificações e hospeda o canal de diagnóstico. Logs grandes são fragmentados; falhas transitórias têm retries limitados e blocos não confirmados permanecem pendentes.

### Facebook e Instagram

Usam Meta Graph API `v26.0`. O Facebook recebe JPEGs por multipart. O Instagram consome URLs assinadas e temporárias do R2; os objetos são removidos após a tentativa de publicação.

### X/Twitter

Usa `tweetkit-x` com cookie de sessão. O cliente é criado sob demanda e invalidado após falha, evitando reutilização de sessão expirada.

### Cloudflare R2

O bucket pode permanecer privado. As URLs são S3v4 com duração de 15 minutos, e os objetos ficam sob prefixos únicos organizados por data.

Veja [integrações](docs/integrations.md).

## Deploy

O CI testa, verifica estilo e ciclos, valida dependências nutricionais, constrói a imagem e publica no GHCR. Pushes em `develop` e `main` acionam os ambientes correspondentes via Komodo. Consulte [operações e deploy](docs/operations.md).

## Troubleshooting

- Startup encerra com código 1: confira as variáveis obrigatórias e o formato de `FIREBASE_JSON`.
- Canal de logs não recebe mensagens: confirme `ID_LOG_CHANNEL`, permissões do bot e `TELEGRAM_LOG_LEVEL`.
- `/tabela` demora na primeira chamada: aguarde o download e carregamento dos modelos.
- Cache não gravável: confira proprietário e permissões do volume.
- Healthcheck falha: confira o scheduler e `HEALTHCHECK_FILE`.
- Publicação social falha: valide credenciais e consulte os logs locais, que preservam traceback sem enviá-lo ao Telegram.

Mais casos em [operações](docs/operations.md).

## Segurança

- Nunca versione `.env`, cookies, contas de serviço, HARs ou arquivos de sessão.
- Rotacione qualquer credencial que tenha sido exposta fora do gerenciador de secrets.
- O canal Telegram recebe contexto sanitizado, não tracebacks, tokens, cookies ou senhas.
- Restrinja o token R2 ao bucket necessário e o token Meta às permissões de publicação.
- O container executa como usuário sem privilégios.

## Desenvolvimento

Mantenha regras de negócio em `modules/`, SDKs e HTTP em `integrations/` e detalhes Telegram em `interfaces/`. Preserve as fachadas existentes ao refatorar e adicione testes para fallbacks, erros e concorrência.

## Licença

Distribuído sob [GNU Affero General Public License v3.0](LICENSE).
