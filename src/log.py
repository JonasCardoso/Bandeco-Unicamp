from telegramServico import mandarMensagem
from util import ID_LOG_CHANNEL


class Log:
    __CHANNEL_ID__ = ID_LOG_CHANNEL
    __log__ = ""

    async def enviarLog(self, context):
        if self.__log__ != "":
            await mandarMensagem(context, self.__CHANNEL_ID__, self.__log__)
        else:
            await mandarMensagem(context, self.__CHANNEL_ID__, "Nenhum registro")
        self.limparLog()

    def limparLog(self):
        self.__log__ = ""

    def adicionarLog(self, log):
        self.__log__ = self.__log__ + log + "\n"
