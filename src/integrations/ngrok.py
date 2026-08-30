"""Gerenciador de túnel ngrok para expor servidor HTTP local.

Este módulo fornece uma classe Ngrok que gerencia um servidor HTTP local
e um túnel ngrok para torná-lo acessível externamente.
"""

import http.server
import shutil
import socketserver
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

import requests

from core.config import get_token_ngrok


def _localizar_ngrok() -> str:
    """Localiza o agente instalado ou o binário local usado em desenvolvimento."""
    instalado = shutil.which("ngrok")
    if instalado:
        return instalado
    return str(Path.cwd() / "ngrok")


class Ngrok:
    """Gerenciador de túnel ngrok com suporte a contexto e thread-safety.

    Attributes:
        ngrok: Processo do ngrok (None se não estiver rodando).
        httpd: Instância do servidor HTTP (None se não estiver rodando).
        _lock: Lock para acesso thread-safe.
        _porta: Porta do servidor HTTP local.
    """

    def __init__(self):
        # Atributos de instância (não compartilhados entre instâncias)
        self.ngrok = None
        self.httpd = None
        self._lock = threading.RLock()
        self._porta = 8000

    def iniciar_servidor(self, log) -> Optional[str]:
        """Inicia o servidor HTTP e túnel ngrok. Thread-safe.

        Args:
            log: Instância de Log para registro de erros.

        Returns:
            URL pública do túnel ou None em caso de erro.
        """
        with self._lock:
            # Se já estiver rodando, desliga primeiro
            if self.ngrok is not None or self.httpd is not None:
                self.desligar_servidor(log)
                time.sleep(2)

            try:
                handler = http.server.SimpleHTTPRequestHandler
                ngrok_bin = _localizar_ngrok()
                subprocess.run(
                    [ngrok_bin, "config", "add-authtoken", get_token_ngrok()],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                )
                self.httpd = socketserver.TCPServer(("", self._porta), handler)
                thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
                thread.start()
                self.ngrok = subprocess.Popen(
                    [ngrok_bin, "http", str(self._porta)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                time.sleep(4)
                resp = requests.get("http://localhost:4040/api/tunnels", timeout=5)
                resp.raise_for_status()
                public_url = resp.json()["tunnels"][0]["public_url"]
                return public_url

            except Exception as error:
                log.adicionar_log(f"iniciar_servidor - 0 - Não foi possível iniciar servidor ngrok\n{error}")
                # Garante limpeza em caso de falha
                self.desligar_servidor(log)
                return None

    def desligar_servidor(self, log):
        """Desliga o servidor HTTP e túnel ngrok."""
        with self._lock:
            self.desligar_ngrok(log)
            self.desligar_httpd(log)

    def desligar_ngrok(self, log):
        """Encerra o processo ngrok."""
        try:
            if self.ngrok is not None:
                self.ngrok.terminate()
                try:
                    self.ngrok.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.ngrok.kill()
                self.ngrok = None

        except Exception as error:
            log.adicionar_log(f"desligar_ngrok - 0 - Não foi possível desligar ngrok\n{error}")

    def desligar_httpd(self, log):
        """Encerra o servidor HTTP."""
        try:
            if self.httpd is not None:
                self.httpd.shutdown()
                self.httpd.server_close()
                self.httpd = None

        except Exception as error:
            log.adicionar_log(f"desligar_httpd - 0 - Não foi possível desligar servidor HTTP\n{error}")

    def __enter__(self):
        """Suporte a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Garante limpeza ao sair do contexto."""
        # Note: não passamos 'log' aqui, então o caller deve chamar desligar_servidor explicitamente se necessário
        return False
