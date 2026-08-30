"""Fixtures compartilhados para todos os testes."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# =============================================================================
# Mocks globais de módulos externos (executados ANTES de qualquer import)
# =============================================================================
# Estes mocks são injetados no sys.modules NO TOPO deste arquivo para que estejam
# disponíveis DURANTE a fase de collection do pytest, antes de qualquer módulo
# da src/ ser importado.


def _inject_external_module_mocks():
    """Injeta mocks nos sys.modules para módulos externos opcionais.

    Deve ser chamado uma vez no topo do conftest.py, ANTES de qualquer
    import dos módulos da src/.
    """

    # --- firebase_admin (banco de dados) ---
    if "firebase_admin" not in sys.modules:
        mock_firebase = MagicMock()
        mock_firebase._apps = []
        mock_firebase.exceptions.FirebaseError = type("FirebaseError", (Exception,), {})
        sys.modules["firebase_admin"] = mock_firebase

        mock_cred = MagicMock()
        mock_cred.Certificate = MagicMock(return_value=MagicMock())
        sys.modules["firebase_admin.credentials"] = mock_cred

        mock_db_ref = MagicMock()
        mock_db_ref.child.return_value.update = MagicMock()
        mock_db = MagicMock()
        mock_db.reference = MagicMock(return_value=mock_db_ref)
        sys.modules["firebase_admin.db"] = mock_db

    # --- matplotlib / pandas / numpy (gráficos e dados) ---
    if "matplotlib" not in sys.modules:
        import matplotlib as _mpl

        _mpl.use("Agg")
        sys.modules["matplotlib"] = _mpl

    if "matplotlib.pyplot" not in sys.modules:
        import matplotlib.pyplot as _plt

        _plt.figure = MagicMock()
        _plt.subplots = MagicMock(return_value=(MagicMock(), MagicMock()))
        _plt.savefig = MagicMock()
        _plt.close = MagicMock()
        sys.modules["matplotlib.pyplot"] = _plt

    if "pandas" not in sys.modules:
        import pandas as _pd

        sys.modules["pandas"] = _pd

    if "numpy" not in sys.modules:
        import numpy as _np

        sys.modules["numpy"] = _np


# Executa a injeção de mocks AGORA, antes de qualquer outro import
_inject_external_module_mocks()


@pytest.fixture(autouse=True)
def mock_firebase_admin():
    """Garante que firebase_admin permaneça mockado durante todo o teste.

    Útil para testes que fazem reload do módulo config.py.
    """
    # Re-injeta mocks caso tenham sido removidos
    if "firebase_admin" not in sys.modules:
        mock_firebase = MagicMock()
        mock_firebase._apps = []
        mock_firebase.exceptions.FirebaseError = type("FirebaseError", (Exception,), {})
        sys.modules["firebase_admin"] = mock_firebase

        mock_cred = MagicMock()
        mock_cred.Certificate = MagicMock(return_value=MagicMock())
        sys.modules["firebase_admin.credentials"] = mock_cred

        mock_db_ref = MagicMock()
        mock_db_ref.child.return_value.update = MagicMock()
        mock_db = MagicMock()
        mock_db.reference = MagicMock(return_value=mock_db_ref)
        sys.modules["firebase_admin.db"] = mock_db

    yield


@pytest.fixture(autouse=True)
def mock_telegram_keyboard_button(monkeypatch):
    """Mock automático do KeyboardButton para todos os testes."""
    # Cria um mock que se comporta como uma string normal
    mock_kb = MagicMock()
    mock_kb.__str__ = lambda self: "KeyboardButton"
    mock_kb.__repr__ = lambda self: "KeyboardButton"

    # Patcha no módulo telegram antes de qualquer importação
    monkeypatch.setattr("telegram.KeyboardButton", mock_kb)


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock automático de todas as variáveis de ambiente para todos os testes."""
    env = {
        "HORARIO_CAFE": "7",
        "HORARIO_ALMOCO": "12",
        "HORARIO_JANTAR": "19",
        "TOKEN_BOT_TELEGRAM": "test_token_123",
        "USERNAME_BOT_TELEGRAM": "bandeco_test_bot",
        "ID_LOG_CHANNEL": "-100123456",
        "URL_BANDECO_PREFEITURA": "https://exemplo.com/prefeitura/",
        "URL_BANDECO_JSON": "https://exemplo.com/json",
        "URL_HORARIO": "https://exemplo.com/horario",
        "URL_SALDO": "https://exemplo.com/saldo",
        "DATABASE_URL_FIREBASE": "https://test.firebaseio.com",
        "FIREBASE_JSON": '{"type":"service_account","project_id":"test","token_uri":"https://oauth2.googleapis.com/token","client_email":"test@test.iam.gserviceaccount.com"}',
        "TWEETKIT_COOKIE": "auth_token=test_auth; ct0=test_csrf",
        "CAM_WEB": "https://exemplo.com/cam/",
        "CAM_RU_A": "ru_a",
        "CAM_RU_B": "ru_b",
        "CAM_RA": "ra",
        "CAM_RS": "rs",
        "CAM_IS_JSON": "false",
        "META_PAGE_ACCESS_TOKEN": "test_meta_page_token",
        "META_GRAPH_API_VERSION": "v26.0",
        "INSTAGRAM_USER_ID": "123456789",
        "FACEBOOK_PAGE_ID": "987654321",
        "R2_ACCOUNT_ID": "test-r2-account",
        "R2_ACCESS_KEY_ID": "test-r2-access",
        "R2_SECRET_ACCESS_KEY": "test-r2-secret",
        "R2_BUCKET": "test-r2-bucket",
    }
    monkeypatch.setattr(os.environ, "clear", lambda: None)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    from core.settings import clear_settings_cache

    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.fixture
def mock_context():
    """Mock do CallbackContext do telegram-bot."""
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    context.bot.delete_message = AsyncMock()
    context.bot.send_photo = AsyncMock()
    return context


@pytest.fixture
def mock_update():
    """Mock do Update do telegram-bot."""
    update = MagicMock()
    update.effective_chat.id = 123456
    update.effective_chat.full_name = "Test User"
    update.effective_chat.username = "testuser"
    update.message = MagicMock()
    update.message.text = ""
    return update


@pytest.fixture
def mock_log():
    """Mock do Log."""
    log = MagicMock()
    log.adicionar_log = MagicMock()
    log.enviar_log = AsyncMock()
    log.limpar_log = MagicMock()
    return log


@pytest.fixture
def sample_cardapio_tradicional():
    """Cardápio de exemplo para testes."""
    return [
        "Frango grelhado com legumes\nArroz integral\nFeijão preto\nSalada verde\n",
        "Tofu grelhado com legumes\nArroz integral\nGrão de bico\nSalada variada\n",
        "",
        "",
        "Café com leite\nAchocolatado\nPão\nMargarina\nGeleia\nFruta\n",
    ]


@pytest.fixture
def sample_cardapio_vegano():
    """Cardápio vegano de exemplo para testes."""
    return [
        "",
        "Strogonoff de cogumelos\nArroz integral\nFeijão preto\nBatata doce\nSalada verde\n",
        "",
        "",
        "Café com leite\nPão\nMargarina\nGeleia\nFruta\n",
    ]


@pytest.fixture
def sample_dados_usuario():
    """Dados de exemplo de usuário para testes."""
    return {
        "tradicional": 1,
        "vegano": 1,
        "cafe": 1,
        "almoco": 1,
        "jantar": 1,
        "telefone": 0,
    }


@pytest.fixture
def sample_dados_usuario_tradicional():
    """Dados de exemplo de usuário apenas tradicional."""
    return {
        "tradicional": 1,
        "vegano": 0,
        "cafe": 1,
        "almoco": 1,
        "jantar": 1,
        "telefone": 0,
    }
