"""Testes unitários para bandeco.py (processamento de cardápios)."""
from unittest.mock import MagicMock

from bandeco import abreviacoes, comida, comida_site_json, comida_site_prefeitura


class TestAbreviacoes:
    """Testes para a função abreviacoes()."""

    def test_abrevia_sigla_no_inicio(self):
        resultado = abreviacoes(['ru'], 'ru de sorvete')
        assert resultado == 'RU de sorvete'

    def test_abrevia_sigla_no_meio(self):
        resultado = abreviacoes(['ra'], 'comida no ra')
        assert resultado == 'comida no RA'

    def test_abrevia_muitas_siglas(self):
        resultado = abreviacoes(['ru', 'ra', 'rs'], 'ru e ra')
        assert 'RU' in resultado
        assert 'RA' in resultado

    def test_nao_abrevia_dentro_de_palavra(self):
        # 'arroz' não deve ser alterado pela sigla 'ra'
        resultado = abreviacoes(['ra'], 'arroz')
        assert resultado == 'arroz'


class TestComidaFallback:
    """Testes para a lógica de fallback do cardápio."""

    def test_comida_retorna_none_se_ambas_as_fontes_falharem(self, monkeypatch):
        # Mock ambas as funções para retornar None
        monkeypatch.setattr('bandeco.comida_site_prefeitura', lambda data: None)
        monkeypatch.setattr('bandeco.comida_site_json', lambda data: None)

        resultado = comida('2024-01-15')
        assert resultado is None

    def test_comida_usa_segunda_fonte_se_primeira_falhar(self, monkeypatch):
        # Primeira fonte falha, segunda succeeds
        monkeypatch.setattr('bandeco.comida_site_prefeitura', lambda data: None)
        monkeypatch.setattr(
            'bandeco.comida_site_json',
            lambda data: ['Almoço tradicional\nFeijão\nArroz\n'],
        )

        resultado = comida('2024-01-15')
        assert resultado is not None
        assert 'Almoço' in resultado[0]


class TestComidaSitePrefeitura:
    """Testes para a função comida_site_prefeitura()."""

    def test_retorna_none_se_nao_existir_cardapio(self, monkeypatch):
        mock_response = MagicMock()
        mock_response.text = 'Não existe cardápio cadastrado no momento !'
        mock_response.status_code = 200
        monkeypatch.setattr('bandeco.req.get', lambda *args, **kwargs: mock_response)

        resultado = comida_site_prefeitura('2024-01-15')
        assert resultado is None

    def test_retorna_none_se_status_diferente_de_200(self, monkeypatch):
        mock_response = MagicMock()
        mock_response.text = 'Erro'
        mock_response.status_code = 500
        monkeypatch.setattr('bandeco.req.get', lambda *args, **kwargs: mock_response)

        resultado = comida_site_prefeitura('2024-01-15')
        assert resultado is None


class TestComidaSiteJson:
    """Testes para a função comida_site_json()."""

    def test_retorna_none_se_erro_no_post(self, monkeypatch):
        mock_response = MagicMock()
        mock_response.text = 'Server-unavailable!'
        mock_response.status_code = 503
        monkeypatch.setattr('bandeco.req.post', lambda *args, **kwargs: mock_response)

        resultado = comida_site_json('2024-01-15')
        assert resultado is None
