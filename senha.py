import base64
import hashlib


def gerarSenhaMD5(senha):
    md5 = hashlib.md5()
    md5.update(senha.encode())
    return md5.digest()


def gerarSenhaSHA256(senha):
    sha256 = hashlib.sha256()
    sha256.update(senha.encode())
    return sha256.digest()


def gerarSenhaSHA512(senha):
    sha512 = hashlib.sha512()
    sha512.update(senha.encode())
    return sha512.digest()


def encodeB64(senha):
    return base64.b64encode(senha).decode('ascii')


def criptografarSenha(senha):
    senhaMD5 = encodeB64(gerarSenhaMD5(senha))
    senhaSHA256 = encodeB64(gerarSenhaSHA256(senha))
    senhaSHA512 = encodeB64(gerarSenhaSHA512(senha))
    return senhaMD5, senhaSHA256, senhaSHA512
