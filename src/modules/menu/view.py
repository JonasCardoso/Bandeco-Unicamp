"""Modelo de leitura independente da interface e adaptador do cardápio legado."""

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")
REFEICOES = {"cafe": "Café da manhã", "almoco": "Almoço", "jantar": "Jantar"}


def hoje() -> date:
    return datetime.now(FUSO).date()


@dataclass(frozen=True)
class Cardapio:
    data: date
    refeicao: str
    modalidade: str
    conteudo: str
    estado: str

    @property
    def texto(self) -> str:
        nome = REFEICOES[self.refeicao]
        if self.refeicao != "cafe":
            nome += f" {self.modalidade}"
        titulo = f"{nome} - {self.data:%d/%m/%Y}"
        mensagens = {
            "erro": "Falha ao consultar a fonte. Tente novamente.",
            "pendente": "Cardápio ainda não publicado para esta data.",
            "ausente": "Refeição não cadastrada.",
        }
        return titulo + "\n\n" + mensagens.get(self.estado, self.conteudo)


def adaptar(dados: list[str] | None, dia: date, refeicao: str, modalidade: str) -> Cardapio:
    indice = {"cafe": 4, "almoco": 0, "jantar": 2}[refeicao]
    if refeicao != "cafe" and modalidade == "vegano":
        indice += 1
    if dados is None or len(dados) <= indice:
        return Cardapio(dia, refeicao, modalidade, "", "erro")
    texto = dados[indice].strip()
    estado = "disponivel"
    if not texto:
        estado = "pendente"
    elif texto == "Refeição não cadastrada.":
        estado = "ausente"
    return Cardapio(dia, refeicao, modalidade, texto, estado)
