# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim-bookworm AS ngrok
ARG TARGETARCH
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && case "${TARGETARCH}" in amd64|arm64) ;; *) echo "Arquitetura não suportada: ${TARGETARCH}" >&2; exit 1 ;; esac \
    && curl --fail --show-error --silent --location \
       "https://bin.ngrok.com/c/bNyj1mQVY4c/ngrok-v3-stable-linux-${TARGETARCH}.tgz" \
       | tar -xz -C /usr/local/bin \
    && ngrok version \
    && rm -rf /var/lib/apt/lists/*

FROM python:${PYTHON_VERSION}-slim-bookworm AS python-deps
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN python -m venv "${VIRTUAL_ENV}"
COPY requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip \
    && python -m pip install --no-compile --index-url "${TORCH_INDEX_URL}" "torch>=2.2,<3" \
    && python -m pip install --no-compile -r /tmp/requirements.txt

FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/matplotlib \
    HF_HOME=/home/bandeco/.cache/huggingface \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=4 \
    MKL_NUM_THREADS=4 \
    MALLOC_ARENA_MAX=2

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 bandeco \
    && useradd --uid 10001 --gid bandeco --create-home --shell /usr/sbin/nologin bandeco \
    && install -d -o bandeco -g bandeco /bandeco /tmp/matplotlib

WORKDIR /bandeco
COPY --from=python-deps /opt/venv /opt/venv
COPY --from=ngrok /usr/local/bin/ngrok /usr/local/bin/ngrok
COPY --chown=bandeco:bandeco src/ ./src/
COPY --chown=bandeco:bandeco .cache_bandeco_nutricao/taco_composicao.csv ./.cache_bandeco_nutricao/
COPY --chown=bandeco:bandeco .cache_bandeco_nutricao/tbca/alimentos.txt ./.cache_bandeco_nutricao/tbca/

USER bandeco
ENTRYPOINT ["python"]
CMD ["src/bot.py"]
