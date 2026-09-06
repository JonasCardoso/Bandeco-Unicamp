# Arquitetura

## Fluxo de inicialização

`app.__main__` chama o bootstrap, que configura timezone/logging, valida Telegram e Firebase, inicializa o repositório, registra jobs e handlers e inicia o polling. Integrações opcionais são validadas somente quando usadas.

## Dependências entre camadas

```text
Telegram / Scheduler
        |
        v
   modules (regras)
        |
        v
 integrations (HTTP, SDKs, persistência)
```

`presentation` gera imagens; `shared` contém infraestrutura pequena e reutilizável. O verificador de imports impede ciclos entre os pacotes internos.

## Concorrência e recursos

Handlers assíncronos usam `asyncio.to_thread` para HTTP síncrono, SDKs e processamento nutricional. O pipeline nutricional mantém um único conjunto de modelos protegido por locks, reutiliza embeddings e descarrega modelos após inatividade. Escritas de cache e imagens usam arquivos temporários e substituição atômica.

## Configuração

`core.settings.Settings` é a fonte tipada e cacheada. `core.config` permanece como fachada compatível. Variáveis essenciais são verificadas no startup; credenciais opcionais falham apenas quando a integração correspondente é acionada.

## Logging

Cada entrada possui severidade, componente, evento, horário e contexto. O logger Python recebe detalhes e traceback; o canal Telegram recebe texto sanitizado. A entrega usa blocos de até 4.000 caracteres, retries limitados para falhas transitórias e retenção do que não foi confirmado.


## Navegação e entregas

A experiência nativa usa callbacks versionados, regras de dias em `modules.preferences.rules` e um modelo de leitura de cardápio independente de Telegram. O transporte de telas retorna identificador e categoria de falha, preservando os helpers booleanos legados. A nutrição é acompanhada por tarefas da aplicação, com concorrência limitada e compartilhamento por conteúdo.

Os jobs recebem a refeição explicitamente e isolam Telegram, Meta e X. Entregas Telegram usam reserva transacional no Firebase, com estado incerto para timeouts. Consulte [fluxos e contratos](telegram-experience.md) para campos, limites, piloto visual e validação.
