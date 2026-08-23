# =============================================================================
# Bandeco-Unicamp Bot — Dockerfile otimizado
# =============================================================================

FROM python:3.10-slim AS base

# Instala dependências do sistema necessárias para opencv
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /bandeco

# =============================================================================
# Camada 1: Dependências Python (cache otimizado)
# Copia apenas requirements.txt primeiro para aproveitar cache do pip
# =============================================================================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Camada 2: Código fonte
# =============================================================================
COPY . .

# Torna o ngrok executável (binário pré-compilado)
RUN chmod +x ngrok

# =============================================================================
# Execução
# =============================================================================
ENTRYPOINT ["python3"]
CMD ["src/bot.py"]

