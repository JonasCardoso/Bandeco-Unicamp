import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from util import DATABASE_URL_FIREBASE

cred = credentials.Certificate('firebase.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': DATABASE_URL_FIREBASE
})


class Config:
    ref = db.reference("/usuarios")

    def adicionar_contato(self, dados, id_user):
        try:
            self.ref.child(str(id_user)).update(dados)
            return True
        except:
            return False

    def atualizar_usuario(self, dados, id_user):
        try:
            self.ref.child(str(id_user)).update(dados)
            return True
        except:
            return False

    def pegar_todos_usuarios(self):
        try:
            item = dict(self.ref.get())
            if len(item) > 0:
                return item
            else:
                return False
        except:
            return False

    def pegar_usuario(self, id_user):
        try:
            item = dict(self.ref.order_by_key().equal_to(str(id_user)).get())
            if len(item) > 0:
                return item[str(id_user)]
            else:
                return False
        except:
            return False

    def criar_usuario(self, id_user):
        try:
            dados = {"tradicional": 1, "vegano": 0, "cafe": 0, "almoco": 1, "jantar": 1, "telefone": 0}
            return self.atualizar_usuario(dados, str(id_user))
        except:
            return False
