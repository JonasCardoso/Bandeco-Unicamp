import base64
import hashlib


def gerar_senha_MD5(senha):
    md5 = hashlib.md5()
    md5.update(senha.encode())
    return md5.digest()


def gerar_senha_SHA256(senha):
    sha256 = hashlib.sha256()
    sha256.update(senha.encode())
    return sha256.digest()


def gerar_senha_SHA512(senha):
    sha512 = hashlib.sha512()
    sha512.update(senha.encode())
    return sha512.digest()


def encodeB64(senha):
    return base64.b64encode(senha).decode('ascii')


def criptografar_senha(senha):
    senha_MD5 = encodeB64(gerar_senha_MD5(senha))
    senha_SHA256 = encodeB64(gerar_senha_SHA256(senha))
    senha_SHA512 = encodeB64(gerar_senha_SHA512(senha))
    return senha_MD5, senha_SHA256, senha_SHA512
