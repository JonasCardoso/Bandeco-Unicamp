from telegram_servico import mandar_mensagem
from util import ID_LOG_CHANNEL


class Log:
    __CHANNEL_ID__ = ID_LOG_CHANNEL
    __log__ = ""

    async def enviar_log(self, context):
        if self.__log__ != "":
            await mandar_mensagem(context, self.__CHANNEL_ID__, self.__log__)
        else:
            pass
        self.limpar_log()

    def limpar_log(self):
        self.__log__ = ""

    def adicionar_log(self, log):
        self.__log__ = self.__log__ + log + "\n"
