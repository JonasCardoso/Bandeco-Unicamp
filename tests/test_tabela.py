"""Testes unitários para tabela.py (geração de tabelas nutricionais com IA)."""
import os
from unittest.mock import MagicMock, patch

import tabela
from tabela import (
    CACHE_TABELA_ARQUIVO,
    _carregar_cache_tabela,
    _salvar_cache_tabela,
    filtrar_csv,
    gerar_tabela_nutricional,
)


class TestFiltrarCSV:
    """Testes para a função filtrar_csv()."""

    def test_filtra_csv_valido(self):
        dados_csv = (
            "Nome;Quantidade;Valor Energético (kcal);Carboidratos (g);Proteínas (g);Gorduras (g);Fibra (g);Sódio (mg)\n"
            "Arroz;100g;130;28;2.7;0.5;0.4;5\n"
            "Feijão;100g;340;60;23;1.5;25;3\n"
        )

        resultado = filtrar_csv(dados_csv)

        assert resultado is not None
        # Deve ter linha de cabeçalho + 2 dados + total
        assert len(resultado) == 4
        # Primeira linha deve ser o cabeçalho
        assert "Nome" in resultado[0]
        # Última linha deve ser o total
        assert resultado[-1][0] == "Total"

    def test_filtra_csv_com_linhas_invalidas(self):
        dados_csv = (
            "Nome;Quantidade;Valor Energético (kcal);Carboidratos (g);Proteínas (g);Gorduras (g);Fibra (g);Sódio (mg)\n"
            "Arroz;100g;130;28;2.7;0.5;0.4;5\n"
            "linha_invalida\n"  # Esta linha deve ser filtrada
        )

        resultado = filtrar_csv(dados_csv)

        assert resultado is not None
        # Apenas cabeçalho + arroz + total (linha inválida filtrada)
        assert len(resultado) == 3

    def test_filtra_csv_vazio(self):
        resultado = filtrar_csv("")

        assert resultado is None


class TestCacheTabela:
    """Testes para funções de cache da tabela nutricional."""

    def test_carregar_cache_nao_existe(self, tmp_path):
        # Garante que o arquivo não existe
        if os.path.exists(CACHE_TABELA_ARQUIVO):
            os.remove(CACHE_TABELA_ARQUIVO)

        resultado = _carregar_cache_tabela()
        assert resultado is None

    def test_salvar_e_carregar_cache(self, tmp_path):
        # Remove cache existente se houver
        if os.path.exists(CACHE_TABELA_ARQUIVO):
            os.remove(CACHE_TABELA_ARQUIVO)

        dados_teste = [["Nome", "Valor"], ["Arroz", "130"]]
        _salvar_cache_tabela(dados_teste)

        assert os.path.exists(CACHE_TABELA_ARQUIVO)

        resultado = _carregar_cache_tabela()
        assert resultado is not None
        assert len(resultado) == 2


class TestGerarTabelaNutricional:
    """Testes para a função gerar_tabela_nutricional()."""

    def test_retorna_none_se_groq_falhar_5_vezes(self):
        # Configura mock que sempre retorna dados inválidos (não é CSV válido)
        call_count = [0]

        def mock_groq_factory(*args, **kwargs):
            mock_client = MagicMock()

            def side_effect(*args, **kwargs):
                call_count[0] += 1
                # Sempre retorna dados inválidos (não é CSV válido)
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "dados inválidos que não são csv"
                return mock_response

            mock_client.chat.completions.create.side_effect = side_effect
            return mock_client

        # Limpa qualquer arquivo de cache existente
        if os.path.exists(tabela.CACHE_TABELA_ARQUIVO):
            os.remove(tabela.CACHE_TABELA_ARQUIVO)

        # Patcha diretamente no módulo tabela usando patch.object
        with patch.object(tabela, 'Groq', MagicMock(side_effect=mock_groq_factory)):
            resultado = gerar_tabela_nutricional("Arroz;100g;130;28;2.7;0.5;0.4;5")

            # Deve tentar 5 vezes e retornar None se todas falharem
            assert call_count[0] == 5, f"Esperado 5 chamadas ao Groq, mas foram {call_count[0]}"
            assert resultado is None
