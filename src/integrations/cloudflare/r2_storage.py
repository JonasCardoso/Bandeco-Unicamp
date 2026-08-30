"""Hospedagem temporária e privada de mídias sociais no Cloudflare R2."""

from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator, Sequence

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from core.config import (
    get_r2_access_key_id,
    get_r2_account_id,
    get_r2_bucket,
    get_r2_secret_access_key,
)

logger = logging.getLogger(__name__)

SIGNED_URL_TTL_SECONDS = 15 * 60


class MediaStorageError(RuntimeError):
    """Indica falha ao disponibilizar uma mídia temporária."""


def _novo_cliente():
    account_id = get_r2_account_id()
    return boto3.client(
        service_name="s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=get_r2_access_key_id(),
        aws_secret_access_key=get_r2_secret_access_key(),
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


@contextmanager
def hospedar_imagens(caminhos: Sequence[Path]) -> Iterator[list[str]]:
    """Envia JPEGs ao R2, fornece URLs temporárias e sempre remove os objetos."""
    cliente = None
    bucket = None
    chaves: list[str] = []
    try:
        cliente = _novo_cliente()
        bucket = get_r2_bucket()
        prefixo = f"social-media/{datetime.now(UTC):%Y-%m-%d}/{uuid.uuid4().hex}"
        urls = []
        for caminho in caminhos:
            chave = f"{prefixo}/{caminho.name}"
            chaves.append(chave)
            with caminho.open("rb") as arquivo:
                cliente.put_object(
                    Bucket=bucket,
                    Key=chave,
                    Body=arquivo,
                    ContentType="image/jpeg",
                )
            urls.append(
                cliente.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": chave},
                    ExpiresIn=SIGNED_URL_TTL_SECONDS,
                )
            )
        yield urls
    except (BotoCoreError, ClientError, OSError, ValueError) as erro:
        raise MediaStorageError("Não foi possível hospedar as imagens temporárias no Cloudflare R2.") from erro
    finally:
        if cliente is not None and bucket is not None:
            for chave in chaves:
                try:
                    cliente.delete_object(Bucket=bucket, Key=chave)
                except (BotoCoreError, ClientError):
                    logger.warning("Falha ao remover objeto temporário do Cloudflare R2: %s", chave)
        if cliente is not None:
            if callable(close := getattr(cliente, "close", None)):
                close()
