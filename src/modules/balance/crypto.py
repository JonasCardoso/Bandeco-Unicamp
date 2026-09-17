"""Utilitários de criptografia de senhas.

Este módulo fornece funções para gerar hashes MD5, SHA256 e SHA512
de senhas, codificadas em Base64, conforme exigido pela API do Bandeco.
"""

import base64
import hashlib


def gerar_senha_MD5(senha: str) -> bytes:
    """Gera hash MD5 da senha.

    Args:
        senha: Senha em texto puro.

    Returns:
        Bytes do hash MD5.
    """
    md5 = hashlib.md5()
    md5.update(senha.encode())
    return md5.digest()


def gerar_senha_SHA256(senha: str) -> bytes:
    """Gera hash SHA256 da senha.

    Args:
        senha: Senha em texto puro.

    Returns:
        Bytes do hash SHA256.
    """
    sha256 = hashlib.sha256()
    sha256.update(senha.encode())
    return sha256.digest()


def gerar_senha_SHA512(senha: str) -> bytes:
    """Gera hash SHA512 da senha.

    Args:
        senha: Senha em texto puro.

    Returns:
        Bytes do hash SHA512.
    """
    sha512 = hashlib.sha512()
    sha512.update(senha.encode())
    return sha512.digest()


def encodeB64(senha: bytes) -> str:
    """Codifica bytes em Base64.

    Args:
        senha: Bytes a serem codificados.

    Returns:
        String codificada em Base64.
    """
    return base64.b64encode(senha).decode("ascii")


def criptografar_senha(senha: str) -> tuple:
    """Gera hashes MD5, SHA256 e SHA512 da senha codificados em Base64.

    Args:
        senha: Senha em texto puro.

    Returns:
        Tupla com (senha_MD5, senha_SHA256, senha_SHA512) em Base64.
    """
    senha_MD5 = encodeB64(gerar_senha_MD5(senha))
    senha_SHA256 = encodeB64(gerar_senha_SHA256(senha))
    senha_SHA512 = encodeB64(gerar_senha_SHA512(senha))
    return senha_MD5, senha_SHA256, senha_SHA512
