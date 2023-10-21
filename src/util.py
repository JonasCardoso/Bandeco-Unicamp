import json
import os


def verificarAtividade(dados, campo):
    return "Inativo" if not dados[campo] else "Ativo"


def salvarJSON(dados, nome):
    with open(f'{nome}.json', 'w', encoding='utf-8') as f:
        json.dump(json.loads(dados), f, ensure_ascii=False, indent=4)


HORARIO_CAFE = int(os.environ['HORARIO_CAFE'])
HORARIO_ALMOCO = int(os.environ['HORARIO_ALMOCO'])
HORARIO_JANTAR = int(os.environ['HORARIO_JANTAR'])
TOKEN_BOT_TELEGRAM = os.environ['TOKEN_BOT_TELEGRAM']
ID_LOG_CHANNEL = os.environ['ID_LOG_CHANNEL']
URL_BANDECO_PREFEITURA = os.environ['URL_BANDECO_PREFEITURA']
URL_BANDECO_JSON = os.environ['URL_BANDECO_JSON']
URL_HORARIO = os.environ['URL_HORARIO']
URL_SALDO = os.environ['URL_SALDO']
DATABASE_URL_FIREBASE = os.environ['DATABASE_URL_FIREBASE']
FIREBASE_JSON = os.environ['FIREBASE_JSON']
URL_SERVICO = os.environ['URL_SERVICO']
API_KEY_TWITTER = os.environ['API_KEY_TWITTER']
API_KEY_SECRET_TWITTER = os.environ['API_KEY_SECRET_TWITTER']
BEARER_TOKEN_TWITTER = os.environ['BEARER_TOKEN_TWITTER']
ACCESS_TOKEN_TWITTER = os.environ['ACCESS_TOKEN_TWITTER']
ACCESS_TOKEN_SECRET_TWITTER = os.environ['ACCESS_TOKEN_SECRET_TWITTER']
CAM_WEB = os.environ['CAM_WEB']
CAM_RU_A = os.environ['CAM_RU_A']
CAM_RU_B = os.environ['CAM_RU_B']
CAM_RA = os.environ['CAM_RA']
CAM_RS = os.environ['CAM_RS']
CAM_IS_JSON = os.environ['CAM_IS_JSON']
INSTAGRAM_ACCESS_TOKEN = os.environ['INSTAGRAM_ACCESS_TOKEN']
INSTAGRAM_USER_ID = os.environ['INSTAGRAM_USER_ID']
INSTAGRAM_GRAPH_URL = os.environ['INSTAGRAM_GRAPH_URL']

PATH_FONTE_LATO_BOLD = 'src/fonte/Lato-Bold.ttf'
PATH_FONTE_LATO_MEDIUM = 'src/fonte/Lato-Medium.ttf'

DIAS = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
MODALIDADES = ['Almoço Tradicional', 'Almoço Vegetariano', 'Jantar Tradicional', 'Jantar Vegetariano', 'Café da manhã']

salvarJSON(FIREBASE_JSON, 'firebase')
