import requests
import http.server
import socketserver
import threading
import subprocess
import time
import socket

from pathlib import Path
from telegram.ext import CallbackContext


def porta_esta_em_uso(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


class Ngrok:
    ngrok = None
    httpd = None

    def iniciar_servidor(self, context: CallbackContext, log):
        if not (self.ngrok is None and self.httpd is None):
            self.desligar_servidor(context, log)

        try:
            PORT = 8000
            handler = http.server.SimpleHTTPRequestHandler
            self.httpd = socketserver.TCPServer(("", PORT), handler)
            thread = threading.Thread(target=self.httpd.serve_forever)
            thread.start()
            self.ngrok = subprocess.Popen([Path(Path().resolve(), "ngrok"), "http", str(PORT)],
                                          stdout=subprocess.PIPE)
            time.sleep(2)
            resp = requests.get("http://localhost:4040/api/tunnels")
            public_url = resp.json()["tunnels"][0]["public_url"]
            return public_url

        except Exception as error:
            log.adicionarLog(f'iniciar_servidor - {0} - Não foi possível iniciar servidor ngrok\n{error}')

    def desligar_servidor(self, context: CallbackContext, log):
        try:
            self.ngrok.terminate()
            self.ngrok.kill()
            self.httpd.shutdown()
            self.httpd.server_close()
            self.ngrok = None
            self.httpd = None

        except Exception as error:
            log.adicionarLog(f'desligar_servidor - {0} - Não foi possível desligar servidor ngrok\n{error}')
