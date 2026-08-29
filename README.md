# Bandeco Unicamp Bot

Bot do Telegram para cardápios dos restaurantes universitários da Unicamp, horários, saldo, câmeras e projeção nutricional.

## Requisitos

- Python 3.12
- Docker com Compose v2 para execução em container
- Credenciais do Telegram e Firebase

Copie `.env.example` para `.env` e preencha as variáveis obrigatórias. `FIREBASE_JSON` aceita o JSON da conta de serviço ou o caminho para um arquivo de credenciais montado. `HF_TOKEN` é opcional e nunca é registrado; quando presente, o Hugging Face Hub o utiliza automaticamente.

## Desenvolvimento local

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest --cov=src --cov-fail-under=65
ruff check src tests
ruff format --check src tests
PYTHONPATH=src python src/bot.py
```

A inicialização acontece explicitamente na ordem: configuração, Firebase, pipeline nutricional, Telegram e polling. Se uma base ou modelo nutricional essencial não puder ser carregado, o polling não começa.

## Docker

```bash
cp .env.example .env
docker compose config
docker compose build
docker compose up -d
```

A imagem usa Python 3.12, roda como usuário não-root (UID/GID 10001) e instala a distribuição CPU do PyTorch pelo índice oficial. O volume `runtime-cache` mantém TACO, TBCA, índices, imagens e modelos do Hugging Face em `/bandeco/.cache_bandeco_nutricao`; `HF_HOME` aponta para o subdiretório gravável `huggingface`.

O primeiro deploy com esta versão baixa novamente os modelos no volume novo. Os volumes antigos `nutrition-cache` e `model-cache` não são removidos automaticamente. Somente depois de validar o deploy e a reutilização do cache, eles podem ser listados e removidos manualmente com `docker volume ls` e `docker volume rm <nome-exato>`.

Para desenvolvimento com a imagem `develop`:

```bash
docker compose -f docker-compose.develop.yaml config
docker compose -f docker-compose.develop.yaml up -d
```

## Estrutura

- `src/settings.py`: fonte única de configuração.
- `src/config.py`: repositório Firebase lazy e compatível via `Config`.
- `src/nutrition/`: parsing, fontes, matching, cálculo, cache e renderização.
- `src/tabela.py`: fachada que preserva os imports antigos.
- `src/bot.py`: composição e startup do processo.

As tabelas nutricionais são estimativas baseadas em TACO/TBCA e modelos de similaridade; não substituem orientação profissional.

## Licença

[AGPL-3.0](./LICENSE)
