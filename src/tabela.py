"""Geração de tabelas nutricionais com IA.

Este módulo fornece funções para gerar imagens de tabelas nutricionais
baseadas em cardápios, utilizando a API Groq (LLM) para estimar valores
nutricionais dos alimentos.
"""

import json
import os
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from groq import Groq
from PIL import Image, ImageOps

from util import get_groq_access_token

# =============================================================================
# Cache para tabela nutricional (TTL: 24 horas)
# =============================================================================

CACHE_TABELA_ARQUIVO = "cache_tabela_nutricional.json"
CACHE_TABELA_TTL_HOURS = 24


def _carregar_cache_tabela() -> dict | None:
    """Carrega o cache da tabela nutricional se ainda for válido."""
    if not os.path.exists(CACHE_TABELA_ARQUIVO):
        return None

    try:
        with open(CACHE_TABELA_ARQUIVO, "r", encoding="utf-8") as f:
            dados = json.load(f)

        timestamp = datetime.fromisoformat(dados["timestamp"])
        if datetime.now() - timestamp > timedelta(hours=CACHE_TABELA_TTL_HOURS):
            # Cache expirado — remove o arquivo
            os.remove(CACHE_TABELA_ARQUIVO)
            return None

        return dados.get("dados")

    except (json.JSONDecodeError, KeyError, ValueError):
        # Arquivo corrompido — remove e tenta regenerar
        if os.path.exists(CACHE_TABELA_ARQUIVO):
            os.remove(CACHE_TABELA_ARQUIVO)
        return None


def _salvar_cache_tabela(dados: list) -> None:
    """Salva os dados da tabela no cache com timestamp atual."""
    try:
        conteudo = {
            "timestamp": datetime.now().isoformat(),
            "dados": dados,
        }
        with open(CACHE_TABELA_ARQUIVO, "w", encoding="utf-8") as f:
            json.dump(conteudo, f, ensure_ascii=False)
    except OSError:
        # Falha ao salvar cache — não impede a geração da tabela
        pass



def filtrar_csv(dados_csv):
    colunas = ['Nome', 'Quantidade', 'Valor Energético (kcal)', 'Carboidratos (g)', 'Proteínas (g)', 'Gorduras (g)',
               'Fibra (g)', 'Sódio (mg)']
    linhas = dados_csv.split("\n")
    dados = [linha.split(";") for linha in linhas]
    dados_filtrados = [linha for linha in dados if len(linha) == 8]

    # Retorna None se não há dados válidos
    if not dados_filtrados:
        return None

    if 'Nome' not in dados_filtrados[0][0]:
        dados_filtrados.insert(0, colunas)
    else:
        dados_filtrados[-1][-1] = dados_filtrados[-1][-1].replace('"', '').replace("'", "")
        dados_filtrados[0][0] = dados_filtrados[0][0].replace('"', '').replace("'", "")

    df = pd.DataFrame(dados_filtrados[1:], columns=colunas)
    try:
        df.set_index('Nome', inplace=True)
    except KeyError:
        return None

    df = df.apply(pd.to_numeric, errors='ignore')
    totais = df.sum(numeric_only=True)
    totais['Quantidade'] = '-'
    df.loc['Total'] = totais
    df = df.round(1)

    return [colunas] + df.reset_index().values.tolist()


def gerar_tabela_nutricional(cardapio):
    # Verifica se existe cache válido antes de chamar o LLM
    cache = _carregar_cache_tabela()
    if cache is not None:
        return _gerar_imagem_tabela(cache)

    prompt = ('''
     Faça uma tabela nutricional seguindo as diretrizes da ANVISA para tabela nutricionais e
     retorne os itens separados por ';' no formato CSV.
     Faça com os seguintes campos:

     Use como base essa quantidade para os tipos de alimentos:
     "Arroz, feijão e mistura: 100g
     Saladas: 50g
     Legumes: 100g
     Refrescos: 250ml
     Frutas: unidade
     Doces: 50g"

     Use essa tabela como base:
     "Nome;Quantidade;Valor Energético (kcal);Carboidratos (g);Proteínas (g);Gorduras (g);Fibra (g);Sódio (mg)
     Cubos suínos ao molho de limão;100g;190;0;27.4;8.2;0;85
     Arroz e feijão;100g;133;26.6;7.9;1.3;3.7;7
     Batata assada com alecrim;100g;112;25.1;1.6;0.2;3.2;10
     Salada de couve;50g;10;2.1;1;0.1;1.3;21
     Maçã;1 unidade;95;25.1;0.5;0.3;4.4;2
     Refresco de pêssego;250ml;120;30;0;0;0;16"

     Para esse cardápio abaixo:
     "Jantar Tradicional de Terça-feira

     Cubos suínos ao molho de limão
     Arroz e feijão
     Batata assada com alecrim
     Salada de couve
     Maçã
     Refresco de pêssego

     Observações:
     Contém glúten no pão francês
     Não contém lactose e ovos


     O cardápio vegano será servido no RU, RA, RS e HC
     O atendimento aos finais de semana e feriados ocorrerá somente no RS"

     Agora gere uma nova tabela nutricional para o cardápio abaixo:\n
     ''')

    prompt = prompt + f'"{cardapio}"\n'
    dados = None

    for i in range(5):
        cliente = Groq(api_key=get_groq_access_token())
        resposta = cliente.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model="mistral-saba-24b",
        )
        dados = filtrar_csv(resposta.choices[0].message.content)

        if dados is not None:
            # Salva no cache para próximas consultas
            _salvar_cache_tabela(dados)
            break
        if i == 4:
            return None

    return _gerar_imagem_tabela(dados)


def _gerar_imagem_tabela(dados):
    """Gera a imagem da tabela a partir dos dados já processados."""
    fig, ax = plt.subplots(figsize=(12, 6))
    tabela = ax.table(cellText=dados, loc='center', cellLoc='center')
    tabela.auto_set_font_size(False)
    tabela.set_fontsize(10)
    tabela.auto_set_column_width(col=list(range(len(dados[0]))))
    ax.axis('off')
    arquivo_temp = "tabela_temporaria.jpg"
    plt.savefig(arquivo_temp, bbox_inches='tight', pad_inches=0)
    plt.close(fig)

    imagem = Image.open(arquivo_temp)
    imagem.load()
    caixa_imagem = tuple(np.asarray(ImageOps.invert(imagem.convert("RGB")).getbbox()))
    imagem_cortada = imagem.crop(caixa_imagem)
    imagem_cortada.save(arquivo_temp)
    return arquivo_temp[:-4]
