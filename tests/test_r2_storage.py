"""Testes do armazenamento temporário de mídias no Cloudflare R2."""

from unittest.mock import MagicMock

import pytest
from botocore.client import Config

from integrations.cloudflare import r2_storage
from integrations.cloudflare.r2_storage import MediaStorageError, hospedar_imagens


def _imagens(tmp_path):
    imagens = [tmp_path / "cardapio.jpg", tmp_path / "observacoes.jpg"]
    for imagem in imagens:
        imagem.write_bytes(b"jpeg")
    return imagens


def test_cliente_usa_endpoint_r2_e_assinatura_v4(monkeypatch):
    boto_client = MagicMock()
    monkeypatch.setattr(r2_storage, "get_r2_account_id", lambda: "conta-123")
    monkeypatch.setattr(r2_storage, "get_r2_access_key_id", lambda: "access-id")
    monkeypatch.setattr(r2_storage, "get_r2_secret_access_key", lambda: "segredo")
    monkeypatch.setattr(r2_storage.boto3, "client", boto_client)

    r2_storage._novo_cliente()

    chamada = boto_client.call_args.kwargs
    assert chamada["service_name"] == "s3"
    assert chamada["endpoint_url"] == "https://conta-123.r2.cloudflarestorage.com"
    assert chamada["region_name"] == "auto"
    assert chamada["aws_access_key_id"] == "access-id"
    assert chamada["aws_secret_access_key"] == "segredo"
    assert isinstance(chamada["config"], Config)
    assert chamada["config"].signature_version == "s3v4"


def test_upload_url_assinada_e_limpeza(tmp_path, monkeypatch):
    imagens = _imagens(tmp_path)
    cliente = MagicMock()
    cliente.generate_presigned_url.side_effect = [
        "https://r2/url-1?X-Amz-Signature=um",
        "https://r2/url-2?X-Amz-Signature=dois",
    ]
    monkeypatch.setattr(r2_storage, "_novo_cliente", lambda: cliente)
    monkeypatch.setattr(r2_storage, "get_r2_bucket", lambda: "bucket-teste")

    with hospedar_imagens(imagens) as urls:
        assert urls == [
            "https://r2/url-1?X-Amz-Signature=um",
            "https://r2/url-2?X-Amz-Signature=dois",
        ]
        assert not cliente.delete_object.called

    puts = cliente.put_object.call_args_list
    chaves = [chamada.kwargs["Key"] for chamada in puts]
    prefixos = [chave.rsplit("/", 1)[0] for chave in chaves]
    assert prefixos[0] == prefixos[1]
    assert prefixos[0].startswith("social-media/")
    assert chaves[0].endswith("/cardapio.jpg")
    for chamada in puts:
        assert chamada.kwargs["Bucket"] == "bucket-teste"
        assert chamada.kwargs["ContentType"] == "image/jpeg"
    for chave, chamada in zip(chaves, cliente.generate_presigned_url.call_args_list, strict=True):
        assert chamada.args == ("get_object",)
        assert chamada.kwargs == {
            "Params": {"Bucket": "bucket-teste", "Key": chave},
            "ExpiresIn": 900,
        }
    assert cliente.delete_object.call_count == 2
    for chave, chamada in zip(chaves, cliente.delete_object.call_args_list, strict=True):
        assert chamada.kwargs == {"Bucket": "bucket-teste", "Key": chave}


def test_limpa_objetos_inclusive_quando_upload_falha(tmp_path, monkeypatch):
    cliente = MagicMock()
    cliente.put_object.side_effect = [{}, OSError("falha local")]
    cliente.generate_presigned_url.return_value = "https://r2/url-assinada"
    monkeypatch.setattr(r2_storage, "_novo_cliente", lambda: cliente)
    monkeypatch.setattr(r2_storage, "get_r2_bucket", lambda: "bucket-teste")

    with pytest.raises(MediaStorageError, match="Cloudflare R2"):
        with hospedar_imagens(_imagens(tmp_path)):
            pytest.fail("o contexto não deve ser entregue após falha de upload")

    assert cliente.delete_object.call_count == 2


def test_falha_na_inicializacao_e_convertida(tmp_path, monkeypatch):
    monkeypatch.setattr(r2_storage, "_novo_cliente", MagicMock(side_effect=ValueError("credencial")))

    with pytest.raises(MediaStorageError, match="Cloudflare R2"):
        with hospedar_imagens(_imagens(tmp_path)):
            pytest.fail("não deve entrar no contexto")


def test_cliente_r2_e_fechado_apos_contexto(tmp_path, monkeypatch):
    cliente = MagicMock()
    cliente.generate_presigned_url.return_value = "https://r2/url-assinada"
    monkeypatch.setattr(r2_storage, "_novo_cliente", lambda: cliente)
    monkeypatch.setattr(r2_storage, "get_r2_bucket", lambda: "bucket-teste")

    with hospedar_imagens(_imagens(tmp_path)[:1]):
        pass

    cliente.close.assert_called_once()
