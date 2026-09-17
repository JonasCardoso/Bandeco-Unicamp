# =============================================================================
# Testes para geração de teclados (teclado.py)
# =============================================================================

from interfaces.telegram.keyboards import (
    teclado_contato,
    teclado_dias_semana,
    teclado_modalidades,
    teclado_notificacao,
)


class TestTecladoDiasSemana:
    """Testes para teclado_dias_semana()."""

    def test_retorna_lista_de_listas(self):
        resultado = teclado_dias_semana("Café", ["Segunda", "Terça"])
        assert isinstance(resultado, list)
        assert all(isinstance(row, list) for row in resultado)

    def test_um_botao_por_linha(self):
        dias = ["Segunda", "Terça", "Quarta"]
        resultado = teclado_dias_semana("Café", dias)
        assert len(resultado) == 3

    def test_cada_linha_tem_um_botao(self):
        resultado = teclado_dias_semana("Almoço", ["Segunda"])
        for linha in resultado:
            assert isinstance(linha, list)
            assert len(linha) == 1


class TestTecladoModalidades:
    """Testes para teclado_modalidades()."""

    def test_retorna_tradicional_e_vegano(self):
        dados = {"tradicional": 1, "vegano": 1}
        resultado = teclado_modalidades(dados)
        assert len(resultado) == 2

    def test_estrutura_correta(self):
        dados = {"tradicional": 1, "vegano": 0}
        resultado = teclado_modalidades(dados)

        for linha in resultado:
            assert isinstance(linha, list)
            assert len(linha) == 1


class TestTecladoNotificacao:
    """Testes para teclado_notificacao()."""

    def test_retorna_tres_periodos(self):
        dados = {"cafe": 1, "almoco": 1, "jantar": 1}
        resultado = teclado_notificacao(dados)
        assert len(resultado) == 3

    def test_estrutura_correta(self):
        dados = {"cafe": 1, "almoco": 0, "jantar": 1}
        resultado = teclado_notificacao(dados)

        for linha in resultado:
            assert isinstance(linha, list)
            assert len(linha) == 1


class TestTecladoContato:
    """Testes para teclado_contato()."""

    def test_retorna_um_botao(self):
        resultado = teclado_contato()
        assert len(resultado) == 1
        assert len(resultado[0]) == 1

    def test_estrutura_correta(self):
        resultado = teclado_contato()
        for linha in resultado:
            assert isinstance(linha, list)
            assert len(linha) == 1
