"""Testes unitários para horario.py (consulta de horários de funcionamento)."""

from unittest.mock import MagicMock, patch

import requests as req

from horario import horario_funcionamento


class TestHorarioFuncionamento:
    """Testes para a função horario_funcionamento()."""

    def test_retorna_horarios_com_sucesso(self):
        html_mock = """
        <div class="block-faq">
            <h5 id="qual-o-horario-de-funcionamento-e-endereco-dos-restaurantes">Horários</h5>
            <div class="block-faq__faq-answer">
                <ul>
                    <li>RU A: 7h às 14h</li>
                    <li>RA: 8h às 20h</li>
                    <li>RS: 9h às 16h</li>
                </ul>
            </div>
        </div>
        """

        mock_response = MagicMock()
        mock_response.text = html_mock

        with patch("horario.requests.get", return_value=mock_response):
            result = horario_funcionamento()

        assert result is not None
        assert "RU A" in result or "7h" in result

    def test_retorna_none_se_elemento_nao_existir(self):
        html_mock = "<div>Conteúdo sem a seção de horários</div>"

        mock_response = MagicMock()
        mock_response.text = html_mock

        with patch("horario.requests.get", return_value=mock_response):
            result = horario_funcionamento()

        assert result is None

    def test_retorna_none_em_erro_de_rede(self):
        with (
            patch("horario.requests.get", side_effect=req.RequestException("Erro de rede")) as requisicao,
            patch("util.time.sleep"),
        ):
            result = horario_funcionamento()

        assert result is None
        assert requisicao.call_count == 3

    def test_retorna_none_se_status_erro(self):
        mock_response = MagicMock()
        mock_response.text = "Erro 500"
        mock_response.status_code = 500

        with patch("horario.requests.get", return_value=mock_response):
            result = horario_funcionamento()

        assert result is None
