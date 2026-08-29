"""Testes do pipeline nutricional consolidado, sem carregar modelos reais."""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

import tabela
from nutrition import cache as nutrition_cache
from tabela import (
    CARDAPIO_EXEMPLO,
    _carregar_cache_tabela,
    _projetar_formato_antigo,
    _salvar_cache_tabela,
    aglutinar_semantica,
    estimar_porcoes_item,
    extrair_itens,
    filtrar_csv,
    normalizar,
    processar_cardapio,
)


def candidato(nome="Arroz, integral, cozido", fonte="TACO", codigo="1"):
    return {
        "codigo": codigo,
        "nome": nome,
        "fonte": fonte,
        "nutrientes": {
            "energia_kcal": 100.0,
            "proteina_g": 3.0,
            "carboidrato_g": 20.0,
            "lipideos_g": 1.0,
            "fibra_g": 2.0,
            "sodio_mg": 5.0,
        },
        "score_embedding": 0.8,
        "score_reranker": 0.9,
        "score_final": 0.9,
    }


def match(query, status="aceito"):
    c = candidato(nome=query)
    return {
        "query": query,
        "status": status,
        "gap": None,
        "resultado": None if status in {"sem_match", "categoria_generica"} else c,
        "candidatos_taco": [c],
        "candidatos_tbca": [],
        "candidatos_reranker": [] if status in {"sem_match", "categoria_generica"} else [c],
    }


class PipelineFalso:
    def __init__(self):
        self.base_taco = [candidato("Feijão, carioca, cozido")]
        self.base_tbca = []
        self.itens = []

    def registrar_itens(self, itens):
        self.itens = list(itens)

    def buscar_referencia(self, query, contexto=None):
        if tabela.chave_texto(query) == "fruta":
            return match(query, "categoria_generica")
        return match(query)


class TestNormalizacaoParser:
    def test_expande_pts_sem_duplicar_descricao(self):
        assert normalizar("PTS") == "proteína texturizada de soja"
        assert normalizar("PTS (PROTEÍNA TEXTURIZADA DE SOJA)") == "proteína texturizada de soja"

    def test_cardapio_principal(self):
        itens = extrair_itens(CARDAPIO_EXEMPLO)
        assert [i["nucleo"] for i in itens[:4]] == [
            "proteína texturizada de soja",
            "arroz integral",
            "feijão",
            "batatas bravas",
        ]
        assert itens[0]["ingredientes"] == ["ervilha partida", "chuchu", "cará"]
        assert itens[3]["ingredientes"] == ["páprica"]
        assert itens[4]["nucleo"] == "beterraba ralada"
        assert len(itens) == 8

    def test_alternativas_e_restaurantes(self):
        itens = extrair_itens("""Almoço Vegano de Segunda-feira
BANANA (RU / HC) / MAÇÃ (RS)
Observações:
Nada.
""")
        assert [i["texto"] for i in itens] == ["BANANA", "MAÇÃ"]
        assert itens[0]["restaurantes"] == ["RU", "HC"]
        assert itens[1]["restaurantes"] == ["RS"]
        assert itens[0]["grupo_alternativa"] == itens[1]["grupo_alternativa"]

    def test_presenca_nao_vira_ingrediente(self):
        item = aglutinar_semantica("STROGONOFF VEGETARIANO (CONTÉM PROTEÍNA DE SOJA)")
        assert item["ingredientes"] == []
        assert item["relacoes"] == [
            {
                "tipo": "presenca",
                "valor": "proteína de soja",
                "origem": "parenteses",
            }
        ]

    def test_lista_explicita_e_condimento(self):
        item = aglutinar_semantica("MOQUECA DE GRÃO DE BICO (CENOURA, TOMATE, ÓLEO DE GERGELIM E LEITE DE COCO)")
        assert item["ingredientes"] == ["cenoura", "tomate", "óleo de gergelim", "leite de coco"]
        tipos = {r["valor"]: r["tipo"] for r in item["relacoes"]}
        assert tipos["óleo de gergelim"] == "condimento"

    def test_generico_fruta_preservado(self):
        itens = extrair_itens("Almoço Vegano\nFRUTA")
        assert itens[0]["nucleo"] == "fruta"
        assert itens[0]["papel"] == "sobremesa"


class TestPorcoesTotais:
    def test_nao_inventa_proporcao_de_componentes(self):
        item = extrair_itens("Almoço Vegano\nPTS com ervilha e chuchu")[0]
        porcoes = estimar_porcoes_item(item)
        assert porcoes["principal"] is None
        assert porcoes["ingredientes"] == {"ervilha": None, "chuchu": None}
        assert not porcoes["proporcoes_conhecidas"]

    def test_prato_simples_completo(self):
        pipeline = PipelineFalso()
        resultado = processar_cardapio("Almoço Vegano\nArroz integral", pipeline)
        assert resultado.totais.iloc[0]["completo"]
        assert resultado.totais.iloc[0]["kcal_est"] == pytest.approx(100.0)

    def test_composto_sem_proporcao_fica_parcial(self):
        pipeline = PipelineFalso()
        resultado = processar_cardapio("Almoço Vegano\nPTS com ervilha e chuchu", pipeline)
        assert not resultado.totais.iloc[0]["completo"]
        assert "proteína texturizada de soja" in resultado.totais.iloc[0]["componentes_sem_referencia"]
        assert set(resultado.componentes["status"]) == {"proporcao_desconhecida"}

    def test_alternativas_geram_cenarios_sem_somar_juntas(self):
        pipeline = PipelineFalso()
        resultado = processar_cardapio("Almoço Vegano\nArroz integral e feijão\nBANANA / MAÇÃ", pipeline)
        assert len(resultado.totais) == 2
        assert all(resultado.totais["completo"])
        assert resultado.totais["kcal_est"].tolist() == [300.0, 300.0]
        dados = _projetar_formato_antigo(resultado)
        assert [linha[0] for linha in dados[-2:]] == ["Total — BANANA", "Total — MAÇÃ"]

    def test_totais_identificam_refresco_e_restaurantes(self):
        pipeline = PipelineFalso()
        resultado = processar_cardapio(
            "Almoço Vegano\nArroz integral\nRefresco de maracujá (RS) / refresco de pêssego (RU/RA/HC/CAISM)",
            pipeline,
        )
        assert resultado.totais["kcal_est"].tolist() == [300.0, 300.0]
        dados = _projetar_formato_antigo(resultado)
        assert [linha[0] for linha in dados[-2:]] == ["Total RS — maracujá", "Total RU/RA/HC/CAISM — pêssego"]

    def test_projecao_mantem_oito_colunas_sem_rotulo_parcial(self):
        pipeline = PipelineFalso()
        resultado = processar_cardapio("Almoço Vegano\nPTS com ervilha", pipeline)
        dados = _projetar_formato_antigo(resultado)
        assert all(len(linha) == 8 for linha in dados)
        assert dados[-1][0] == "Total"

    def test_quantidade_usa_gramas_para_solidos_e_ml_para_bebidas(self):
        pipeline = PipelineFalso()
        resultado = processar_cardapio("Almoço Vegano\nArroz integral\nRefresco de pêssego", pipeline)
        dados = _projetar_formato_antigo(resultado)
        assert dados[1][1] == "100g"
        assert dados[2][1] == "200ml"

    def test_descarga_modelos_somente_quando_ociosos(self):
        marcador = object()
        base_taco = [{"nome": "arroz"}]
        pipeline = tabela.PipelineNutricional(
            base_taco,
            [],
            marcador,
            marcador,
            None,
            None,
            "cpu",
            marcador,
            marcador,
            {},
        )
        assert tabela.TEMPO_OCIOSO_MODELOS_SEGUNDOS == 300
        pipeline._usos_modelos = 1
        pipeline._descarregar_modelos_se_ocioso()
        assert pipeline.embedding_model is marcador
        pipeline._usos_modelos = 0
        pipeline._descarregar_modelos_se_ocioso()
        assert pipeline.base_taco is base_taco
        assert (
            pipeline.embedding_model,
            pipeline.reranker,
            pipeline.embeddings_taco,
            pipeline.embeddings_tbca,
        ) == (None, None, None, None)


class TestInicializacaoPipeline:
    def test_preflight_informa_cache_sem_permissao(self, tmp_path, monkeypatch):
        cache = tmp_path / "hf-cache"
        monkeypatch.setenv("HF_HOME", str(cache))
        criar_temporario = nutrition_cache.tempfile.NamedTemporaryFile

        def negar_escrita(*args, **kwargs):
            if Path(kwargs["dir"]) == cache:
                raise PermissionError("sem permissão")
            return criar_temporario(*args, **kwargs)

        monkeypatch.setattr(nutrition_cache.tempfile, "NamedTemporaryFile", negar_escrita)
        with pytest.raises(tabela.DadosNutricionaisIndisponiveis, match="cache não gravável") as erro:
            tabela.validar_cache_gravavel()
        assert str(cache) in str(erro.value)
        assert "uid=" in str(erro.value)

    def test_inicializacao_reutiliza_singleton(self, monkeypatch):
        pipeline = object()
        carregamentos = []
        monkeypatch.setattr(tabela, "_PIPELINE", None)
        monkeypatch.setattr(
            tabela.PipelineNutricional,
            "carregar",
            staticmethod(lambda: carregamentos.append(1) or pipeline),
        )
        assert tabela.inicializar_pipeline_nutricional() is pipeline
        assert tabela.inicializar_pipeline_nutricional() is pipeline
        assert tabela.obter_pipeline() is pipeline
        assert carregamentos == [1]


class TestCacheECsv:
    def test_cache_distingue_cardapio(self, tmp_path, monkeypatch):
        caminho = tmp_path / "cache.json"
        monkeypatch.setattr(tabela, "CACHE_TABELA_ARQUIVO", str(caminho))
        _salvar_cache_tabela([["a"]], "hash-a")
        assert _carregar_cache_tabela("hash-a") == [["a"]]
        assert _carregar_cache_tabela("hash-b") is None

    def test_filtrar_csv_compativel(self):
        csv_texto = (
            "Nome;Quantidade;Valor Energético (kcal);Carboidratos (g);Proteínas (g);"
            "Gorduras (g);Fibra (g);Sódio (mg)\nArroz;100g;130;28;2.7;0.5;0.4;5\n"
        )
        dados = filtrar_csv(csv_texto)
        assert dados is not None and dados[-1][0] == "Total"
        assert len(dados[0]) == 8

    def test_vazio(self):
        assert filtrar_csv("") is None
        assert extrair_itens("") == []


class TestHistoricoReal:
    def test_parser_em_todo_historico(self):
        raiz = Path(__file__).parents[1]
        arquivos = sorted((raiz / "historico").glob("messages*.html"))
        if not arquivos:
            pytest.skip("histórico não disponível")
        total = 0
        for arquivo in arquivos:
            soup = BeautifulSoup(arquivo.read_text(encoding="utf-8"), "html.parser")
            for elemento in soup.select("div.message div.text"):
                texto = elemento.get_text("\n", strip=True)
                if not tabela._titulo(texto.splitlines()[0] if texto else ""):
                    continue
                itens = extrair_itens(texto)
                assert itens
                assert all(not tabela._titulo(i["texto"]) for i in itens)
                assert all("observações:" not in i["texto"].lower() for i in itens)
                total += 1
        assert total == 6452
