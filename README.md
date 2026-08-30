# Bandeco Unicamp Bot

Bot do Telegram para cardápios dos restaurantes universitários da Unicamp, horários, saldo, câmeras e projeção nutricional.

## Requisitos

- Python 3.12
- Docker com Compose v2 para execução em container
- Credenciais do Telegram e Firebase

Copie `.env.example` para `.env`, na raiz do repositório, e preencha as variáveis obrigatórias. `FIREBASE_JSON` aceita o JSON da conta de serviço ou o caminho para um arquivo de credenciais montado. `HF_TOKEN` é opcional e nunca é registrado; quando presente, o Hugging Face Hub o utiliza automaticamente.

## Desenvolvimento local

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest --cov=src --cov-fail-under=65
ruff check src tests
ruff format --check src tests
PYTHONPATH=src python -m app
```

No PowerShell, defina o caminho de imports antes de iniciar:

```powershell
$env:PYTHONPATH = "src"
python -m app
```

Execute os comandos a partir da raiz do repositório. `src` é o diretório-raiz do código e não é um pacote Python; `app` é o entrypoint. A inicialização acontece explicitamente na ordem: configuração, Firebase, Telegram e polling. O pipeline nutricional é lazy: modelos são carregados somente quando a tabela é solicitada e podem ser liberados após o período de ociosidade.

## Facebook e Instagram

A publicação usa exclusivamente a Meta Graph API `v26.0` com Facebook Login e um Page Access Token. Configure `META_PAGE_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID`, `INSTAGRAM_USER_ID`, `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` e `R2_BUCKET`. O token deve ter as permissões `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic` e `instagram_content_publish`; a conta profissional do Instagram precisa estar vinculada à Página.

As imagens do Facebook são enviadas diretamente por multipart. Para o Instagram, o bot envia JPEGs temporários a um bucket privado do Cloudflare R2, gera URLs S3v4 válidas por 15 minutos e remove os objetos ao terminar, inclusive em caso de falha. O token R2 precisa das permissões de leitura e escrita de objetos no bucket escolhido. `R2_PUBLIC_URL` não é necessária e o acesso público ao bucket pode permanecer desativado. URLs assinadas, tokens e credenciais não são registrados.

Consulte a [coleção oficial da Instagram API](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api) e a [documentação oficial do R2 com boto3 e URLs pré-assinadas](https://developers.cloudflare.com/r2/examples/aws/boto3/).

## Docker

```bash
cp .env.example .env
docker compose config
docker build --check .
docker compose build
docker compose up -d
```

A imagem usa Python 3.12, roda como usuário não-root (UID/GID 10001) e inicia com `python -m app`. A distribuição CPU do PyTorch é instalada pelo índice oficial.

O volume `runtime-cache` mantém TACO, TBCA, índices, imagens e modelos do Hugging Face em `/bandeco/.cache_bandeco_nutricao`; `HF_HOME` aponta para o subdiretório gravável `huggingface`.

O primeiro deploy com esta versão baixa novamente os modelos no volume novo. Os volumes antigos `nutrition-cache` e `model-cache` não são removidos automaticamente. Somente depois de validar o deploy e a reutilização do cache, eles podem ser listados e removidos manualmente com `docker volume ls` e `docker volume rm <nome-exato>`.

Para desenvolvimento com a imagem `develop`:

```bash
docker compose -f docker-compose.develop.yaml config
docker compose -f docker-compose.develop.yaml up -d
```

## Estrutura

O código está organizado diretamente sob `src/`:

- `app/`: entrypoint, bootstrap, agendamento e registro de handlers.
- `core/`: settings, constantes e acesso tipado à configuração.
- `shared/`: retry, rate limiting e operações genéricas de arquivo.
- `modules/`: regras de cardápio, saldo, câmeras, notificações, preferências e nutrição.
- `integrations/`: clientes Unicamp, Firebase, Cloudflare R2, Meta e Twitter.
- `interfaces/telegram/`: handlers, comandos, teclados, mensagens e logging.
- `presentation/`: geração de imagens e assets gráficos.

Os imports internos usam esses pacotes diretamente, por exemplo `from core.config import get_bot_username`. Não existem módulos planos ou fachadas legadas na raiz de `src`.

As tabelas nutricionais são estimativas baseadas em TACO/TBCA e modelos de similaridade; não substituem orientação profissional.

## Licença

[AGPL-3.0](./LICENSE)
