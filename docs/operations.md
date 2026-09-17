# Operações, deploy e troubleshooting

## Validação antes do deploy

```bash
python -m pytest --cov=src --cov-fail-under=65
ruff check src tests tools
ruff format --check src tests tools
python tools/check_import_cycles.py
docker compose config --quiet
docker build --check .
docker build -t bandeco-unicamp:local .
```

## CI/CD

Pull requests executam testes, lint, verificação de ciclos, imports nutricionais e build sem publicação. Pushes publicam tags por branch no GHCR. Os jobs self-hosted solicitam o deploy das stacks de desenvolvimento ou produção ao Komodo.

## Cache e volumes

O volume `runtime-cache` contém bases TACO/TBCA, modelos, embeddings, catálogo derivado, metadados e imagens nutricionais. TACO e TBCA são entradas versionadas; catálogo, embeddings e imagens são regeneráveis e não devem ser commitados.

O antigo `cache_tabela_nutricional.json` na raiz é lido como fallback e migrado para `.cache_bandeco_nutricao/cache_tabela_nutricional.json`.

## Healthcheck

O scheduler atualiza `HEALTHCHECK_FILE`. O comando `python -m shared.health` retorna sucesso apenas quando o heartbeat existe e é recente. Em falha, verifique se o bot iniciou, se o job queue está ativo e se o diretório é gravável.

## Logging

`LOG_LEVEL` controla stdout/stderr; `TELEGRAM_LOG_LEVEL` controla o canal. O canal deve ser administrado pelo bot identificado por `ID_LOG_CHANNEL`. Rate limits e indisponibilidade de rede recebem retries limitados. Erros permanentes ficam no buffer e no logger local sem loop recursivo.

## Incidentes de credenciais

1. Revogue ou rotacione a credencial.
2. Atualize o secret do ambiente, nunca o repositório.
3. Reinicie a stack.
4. Verifique logs e histórico Git sem copiar o segredo para tickets ou chats.
5. Se necessário, reescreva o histórico em um procedimento separado e explicitamente aprovado.

## Falhas comuns

- Firebase inválido: valide se `FIREBASE_JSON` é JSON válido ou caminho montado e legível.
- Modelos não carregam: confira espaço, memória, acesso ao Hugging Face e permissões do volume.
- Meta retorna autenticação: renove o Page Access Token e confirme vínculo da conta Instagram.
- R2 falha: confirme endpoint, bucket e permissões de objeto.
- X falha repetidamente: substitua o cookie de sessão.
- Docker unhealthy: verifique logs do processo, heartbeat e relógio do host.

