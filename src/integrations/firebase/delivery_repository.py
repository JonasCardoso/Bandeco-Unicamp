"""Registro de entregas com reserva transacional; timeout não significa falha certa."""

import time
from uuid import uuid4

from firebase_admin import db

from integrations.firebase.user_repository import inicializar_firebase


class DeliveryRepository:
    def __init__(self, ref=None):
        if ref is None:
            inicializar_firebase()
            ref = db.reference("/entregas")
        self.ref = ref

    def reservar(self, destinatario, chave):
        token = uuid4().hex
        agora = time.time()

        def reservar(atual):
            if atual and atual.get("estado") in {"confirmado", "incerto", "bloqueado"}:
                return atual
            if atual and atual.get("estado") == "enviando":
                # Um processo caiu com envio em curso: requer revisão, não reenvio cego.
                if agora - atual.get("quando", agora) > 600:
                    return {**atual, "estado": "incerto"}
                return atual
            return {"estado": "enviando", "token": token, "quando": agora}

        resultado = self.ref.child(str(destinatario)).child(chave).transaction(reservar)
        return (
            token if resultado and resultado.get("token") == token and resultado.get("estado") == "enviando" else None
        )

    def estado(self, destinatario, chave):
        registro = self.ref.child(str(destinatario)).child(chave).get()
        return registro.get("estado", "desconhecido") if registro else "desconhecido"

    def concluir(self, destinatario, chave, token, estado, message_id=None):
        def atualizar(atual):
            if atual and atual.get("token") == token:
                return {"estado": estado, "quando": time.time(), "message_id": message_id}
            return atual

        self.ref.child(str(destinatario)).child(chave).transaction(atualizar)
