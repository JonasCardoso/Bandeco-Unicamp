"""Constantes estáveis compartilhadas pela aplicação."""

from pathlib import Path

DIAS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
MODALIDADES = ["Almoço Tradicional", "Almoço Vegano", "Jantar Tradicional", "Jantar Vegano", "Café da manhã"]

ASSETS_DIR = Path(__file__).resolve().parents[1] / "presentation" / "assets"
PATH_FONTE_LATO_BOLD = str(ASSETS_DIR / "fonts" / "Lato-Bold.ttf")
PATH_FONTE_LATO_MEDIUM = str(ASSETS_DIR / "fonts" / "Lato-Medium.ttf")
