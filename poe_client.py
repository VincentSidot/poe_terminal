import poe
from logger import Logger

class PoeError(Exception):
    def __init__(self, message):
        self.message = message
    
    def __str__(self):
        return self.message

class Poe:
    __current_bot = None
    __bots = {}
    __client = None

    def __init__(self, token):
        self.__client = poe.Client(token)
        self.__bots = self.__client.bot_names
        self.__current_bot = list(self.__bots.keys())[0]
    
    @property
    def bots(self):
        return self.__bots
    
    def show_bots(self) -> str:
        buffer = ""
        for bot in self.__bots:
            buffer += f"{self.__bots[bot]} ({bot})\n"
        return buffer

    @property
    def bot(self):
        return self.__current_bot
    
    @bot.setter
    def bot(self, bot) -> None:
        if bot in self.__bots:
            self.__current_bot = bot
        else:
            raise PoeError("Invalid bot name or index")
    
    def set_bot(self, bot) -> None:
        self.bot = bot

    def send_chat_break(self) -> None:
        self.__client.send_chat_break(self.__current_bot)

    def send_message_generator(self, message) -> str:
        Logger(f"Sent message: {message}")
        for chunk in self.__client.send_message(self.__current_bot, message):
            text = chunk["text_new"]
            yield text
        Logger(f"Received chunks: {chunk}")

    def send_message(self, message) -> str:
        for chunk in self.__client.send_message(self.__current_bot, message):
            pass
        Logger(f"Sent message: {message}\nReceived chunk: {chunk}")
        text = chunk["text"]
        return text
        