"""Testes unitários para cardapio.py (lógica pura de processamento de cardápio)."""

from cardapio import formatar_cardapio_para_mensagem, modalidade_com_cardapio
from util import MODALIDADES


class TestModalidadeComCardapio:
    """Testes para a função modalidade_com_cardapio()."""

    def test_almoço_tradicional_apenas(self, sample_cardapio_tradicional, sample_dados_usuario_tradicional):
        resultado = modalidade_com_cardapio(
            sample_cardapio_tradicional,
            sample_dados_usuario_tradicional,
            'Almoço'
        )

        assert len(resultado) == 1
        assert 'Tradicional' in resultado[0][1]

    def test_almoço_vegano_apenas(self, sample_cardapio_vegano):
        dados = {"tradicional": 0, "vegano": 1, "cafe": 0, "almoco": 1, "jantar": 1}
        resultado = modalidade_com_cardapio(sample_cardapio_vegano, dados, 'Almoço')

        assert len(resultado) == 1
        assert 'Vegano' in resultado[0][1]

    def test_almoço_tradicional_e_vegano(self, sample_cardapio_tradicional):
        dados = {"tradicional": 1, "vegano": 1, "cafe": 0, "almoco": 1, "jantar": 1}
        resultado = modalidade_com_cardapio(sample_cardapio_tradicional, dados, 'Almoço')

        assert len(resultado) == 2
        modalidades = [r[1] for r in resultado]
        # Verifica se ambas as modalidades estão presentes
        assert any('Tradicional' in m for m in modalidades)
        assert any('Vegano' in m for m in modalidades)

    def test_almoço_sem_preferencias_mostra_ambos(self, sample_cardapio_tradicional):
        # Quando tradicional=0 e vegano=0, mostra ambos (comportamento padrão)
        dados = {"tradicional": 0, "vegano": 0, "cafe": 0, "almoco": 1, "jantar": 1}
        resultado = modalidade_com_cardapio(sample_cardapio_tradicional, dados, 'Almoço')

        assert len(resultado) == 2

    def test_cafe_da_manha(self, sample_cardapio_tradicional):
        resultado = modalidade_com_cardapio(
            sample_cardapio_tradicional,
            {"tradicional": 1, "vegano": 0, "cafe": 1, "almoco": 0, "jantar": 0},
            'Café da manhã'
        )

        assert len(resultado) == 1
        assert 'Café' in resultado[0][1]

    def test_jantar_tradicional(self, sample_cardapio_tradicional):
        dados = {"tradicional": 1, "vegano": 0, "cafe": 0, "almoco": 0, "jantar": 1}
        resultado = modalidade_com_cardapio(sample_cardapio_tradicional, dados, 'Jantar')

        assert len(resultado) == 1
        assert 'Tradicional' in resultado[0][1]

    def test_jantar_vegano(self, sample_cardapio_vegano):
        dados = {"tradicional": 0, "vegano": 1, "cafe": 0, "almoco": 0, "jantar": 1}
        resultado = modalidade_com_cardapio(sample_cardapio_vegano, dados, 'Jantar')

        assert len(resultado) == 1
        assert 'Vegano' in resultado[0][1]


class TestFormatarCardapioParaMensagem:
    """Testes para a função formatar_cardapio_para_mensagem()."""

    def test_formata_cardapio_com_um_item(self):
        cardapio = [("Frango grelhado\nArroz\nFeijão", "Almoço Tradicional")]
        resultado = formatar_cardapio_para_mensagem(cardapio, 'Segunda-feira')

        assert len(resultado) == 1
        assert '*Almoço Tradicional de Segunda-feira*' in resultado[0]
        assert 'Frango grelhado' in resultado[0]

    def test_formata_cardapio_com_dois_itens(self):
        cardapio = [
            ("Frango grelhado\nArroz", "Almoço Tradicional"),
            ("Tofu grelhado\nFeijão", "Almoço Vegano"),
        ]
        resultado = formatar_cardapio_para_mensagem(cardapio, 'Quarta-feira')

        assert len(resultado) == 2
        assert '*Almoço Tradicional de Quarta-feira*' in resultado[0]
        assert '*Almoço Vegano de Quarta-feira*' in resultado[1]

    def test_ignera_refeicao_nao_cadastrada(self):
        cardapio = [
            ("Refeição não cadastrada.", "Almoço Tradicional"),
            ("Tofu grelhado", "Almoço Vegano"),
        ]
        resultado = formatar_cardapio_para_mensagem(cardapio, 'Segunda-feira')

        assert len(resultado) == 1
        assert 'Refeição não cadastrada' not in resultado[0]


class TestModalidadesConstant:
    """Testes para a constante MODALIDADES."""

    def test_modalidades_importadas_do_util(self):
        assert len(MODALIDADES) == 5
        assert 'Almoço Tradicional' in MODALIDADES
        assert 'Almoço Vegano' in MODALIDADES
        assert 'Jantar Tradicional' in MODALIDADES
        assert 'Jantar Vegano' in MODALIDADES
        assert 'Café da manhã' in MODALIDADES
