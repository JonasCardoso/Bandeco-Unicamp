# =============================================================================
# Testes para funções de criptografia de senhas (senha.py)
# =============================================================================
import base64

from senha import (
    criptografar_senha,
    encodeB64,
    gerar_senha_MD5,
    gerar_senha_SHA256,
    gerar_senha_SHA512,
)


class TestGerarSenhaMD5:
    """Testes para gerar_senha_MD5()."""

    def test_retorna_bytes(self):
        resultado = gerar_senha_MD5('test')
        assert isinstance(resultado, bytes)

    def test_consistente_mesma_senha(self):
        r1 = gerar_senha_MD5('senha123')
        r2 = gerar_senha_MD5('senha123')
        assert r1 == r2

    def test_diferente_para_senhas_diferentes(self):
        assert gerar_senha_MD5('senha1') != gerar_senha_MD5('senha2')


class TestGerarSenhaSHA256:
    """Testes para gerar_senha_SHA256()."""

    def test_retorna_bytes(self):
        resultado = gerar_senha_SHA256('test')
        assert isinstance(resultado, bytes)

    def test_consistente_mesma_senha(self):
        r1 = gerar_senha_SHA256('senha123')
        r2 = gerar_senha_SHA256('senha123')
        assert r1 == r2


class TestGerarSenhaSHA512:
    """Testes para gerar_senha_SHA512()."""

    def test_retorna_bytes(self):
        resultado = gerar_senha_SHA512('test')
        assert isinstance(resultado, bytes)

    def test_consistente_mesma_senha(self):
        r1 = gerar_senha_SHA512('senha123')
        r2 = gerar_senha_SHA512('senha123')
        assert r1 == r2


class TestEncodeB64:
    """Testes para encodeB64()."""

    def test_retorna_string(self):
        resultado = encodeB64(b'test')
        assert isinstance(resultado, str)

    def test_decodifica_corretamente(self):
        original = b'hello world'
        encoded = encodeB64(original)
        decoded = base64.b64decode(encoded).decode('ascii')
        assert decoded == 'hello world'


class TestCriptografarSenha:
    """Testes para criptografar_senha()."""

    def test_retorna_tripla(self):
        resultado = criptografar_senha('test')
        assert isinstance(resultado, tuple)
        assert len(resultado) == 3

    def test_retorna_strings_base64(self):
        md5, sha256, sha512 = criptografar_senha('test')
        assert isinstance(md5, str)
        assert isinstance(sha256, str)
        assert isinstance(sha512, str)

    def test_consistente_mesma_senha(self):
        r1 = criptografar_senha('senha123')
        r2 = criptografar_senha('senha123')
        assert r1 == r2

    def test_diferente_para_senhas_diferentes(self):
        assert criptografar_senha('senha1') != criptografar_senha('senha2')
