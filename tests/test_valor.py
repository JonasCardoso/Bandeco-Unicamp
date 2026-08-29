"""Testes do parser e da apresentação dos valores das refeições."""

from unittest.mock import MagicMock

import valor


def test_extrair_tabela_html(monkeypatch):
    response = MagicMock()
    response.text = """
        <h1>Valor da Refeição – Restaurante Universitário</h1>
        <figure class="wp-block-table"><table>
          <tr><th>Categoria</th><th>Valor</th></tr>
          <tr><td>Estudantes</td><td>R$ 3,00</td></tr>
          <tr><td>Visitantes</td><td>R$ 15,00</td></tr>
        </table></figure>
    """
    monkeypatch.setattr(valor.requests, "get", lambda *args, **kwargs: response)

    assert valor._extrair_tabela("https://example.test") == (
        "Restaurante Universitário",
        [("Estudantes", "R$ 3,00"), ("Visitantes", "R$ 15,00")],
    )
    response.raise_for_status.assert_called_once_with()


def test_extrair_tabela_rejeita_html_incompleto(monkeypatch):
    response = MagicMock(text="<h1>Sem tabela</h1>")
    monkeypatch.setattr(valor.requests, "get", lambda *args, **kwargs: response)
    assert valor._extrair_tabela("https://example.test") is None


def test_obter_valores_formata_resultados_parciais(monkeypatch):
    respostas = iter([("Café", [("Estudantes", "R$ 2,00")]), None])
    monkeypatch.setattr(valor, "_extrair_tabela", lambda _url: next(respostas))
    texto = valor.obter_valores_refeicao()
    assert "VALOR DAS REFEIÇÕES" in texto
    assert "Café da Manhã" in texto
    assert "R$ 2,00" in texto
    assert "Almoço e Jantar" not in texto


def test_obter_valores_formata_almoco(monkeypatch):
    respostas = iter([None, ("Almoço", [("Visitantes", "R$ 15,00")])])
    monkeypatch.setattr(valor, "_extrair_tabela", lambda _url: next(respostas))
    texto = valor.obter_valores_refeicao()
    assert "Almoço e Jantar" in texto
    assert "R$ 15,00" in texto


def test_obter_valores_retorna_none_quando_ambas_falham(monkeypatch):
    monkeypatch.setattr(valor, "_extrair_tabela", lambda _url: None)
    assert valor.obter_valores_refeicao() is None


def test_obter_valores_trata_erro_inesperado(monkeypatch):
    monkeypatch.setattr(valor, "_extrair_tabela", lambda _url: 1 / 0)
    assert valor.obter_valores_refeicao() is None
