import requests
import http.server
import socketserver
import threading
import subprocess
import time

from pathlib import Path
from util import TOKEN_NGROK


class Ngrok:
    ngrok = None
    httpd = None

    def iniciar_servidor(self, log):
        if self.ngrok is not None or self.httpd is not None:
            self.desligar_servidor(log)
            time.sleep(2)

        try:
            porta = 8000
            handler = http.server.SimpleHTTPRequestHandler
            subprocess.run([Path(Path().resolve(), "ngrok"), 'config', 'add-authtoken', TOKEN_NGROK],
                           stdout=subprocess.PIPE)
            self.httpd = socketserver.TCPServer(("", porta), handler)
            thread = threading.Thread(target=self.httpd.serve_forever)
            thread.start()
            self.ngrok = subprocess.Popen([Path(Path().resolve(), "ngrok"), "http", str(porta)],
                                          stdout=subprocess.PIPE)
            time.sleep(4)
            resp = requests.get("http://localhost:4040/api/tunnels")
            public_url = resp.json()["tunnels"][0]["public_url"]
            return public_url

        except Exception as error:
            log.adicionar_log(f'iniciar_servidor - {0} - Não foi possível iniciar servidor ngrok\n{error}')

    def desligar_servidor(self, log):
        self.desligar_ngrok(log)
        self.desligar_httpd(log)

    def desligar_ngrok(self, log):
        try:
            self.ngrok.terminate()
            self.ngrok.kill()
            self.ngrok = None

        except Exception as error:
            log.adicionar_log(f'desligar_ngrok - {0} - Não foi possível desligar servidor ngrok\n{error}')

    def desligar_httpd(self, log):
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None

        except Exception as error:
            log.adicionar_log(f'desligar_httpd - {0} - Não foi possível desligar servidor ngrok\n{error}')
