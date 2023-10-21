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

    def adicionarContato(self, dados, id):
        try:
            self.ref.child(str(id)).update(dados)
            return True
        except:
            return False

    def atualizarUsuario(self, dados, id):
        try:
            self.ref.child(str(id)).update(dados)
            return True
        except:
            return False

    def pegarTodosUsuarios(self):
        try:
            item = dict(self.ref.get())
            if len(item) > 0:
                return item
            else:
                return False
        except:
            return False

    def pegarUsuario(self, id):
        try:
            item = dict(self.ref.order_by_key().equal_to(str(id)).get())
            if len(item) > 0:
                return item[str(id)]
            else:
                return False
        except:
            return False

    def criarUsuario(self, id):
        try:
            dados = {"tradicional": 1, "vegano": 0, "cafe": 0, "almoco": 1, "jantar": 1, "telefone": 0}
            return self.atualizarUsuario(dados, str(id))
        except:
            return False
