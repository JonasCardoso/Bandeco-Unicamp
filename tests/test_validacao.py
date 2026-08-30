"""Testes unitários para validacao.py (validação de entrada de saldo)."""

from modules.balance.validation import validar_saldo_entrada


class TestValidarSaldoEntrada:
    """Testes para a função validar_saldo_entrada()."""

    def test_ra_valido_e_senha_valida(self):
        assert validar_saldo_entrada("123456", "abc123") is True

    def test_ra_muito_curto(self):
        assert validar_saldo_entrada("12", "abc123") is False

    def test_ra_muito_longo(self):
        assert validar_saldo_entrada("1" * 20, "abc123") is False

    def test_ra_com_letras(self):
        assert validar_saldo_entrada("abc123", "abc123") is False

    def test_senha_muito_curta(self):
        assert validar_saldo_entrada("123456", "ab") is False

    def test_ra_e_senha_validos_minimos(self):
        # RA mínimo de 3 caracteres, senha mínima de 3 caracteres
        assert validar_saldo_entrada("123", "abc") is True

    def test_senha_com_espaco(self):
        assert validar_saldo_entrada("123456", "ab cd") is False

    def test_ra_vazio(self):
        assert validar_saldo_entrada("", "abc123") is False

    def test_senha_vazia(self):
        assert validar_saldo_entrada("123456", "") is False
