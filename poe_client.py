import poe


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
    
    def show_bots(self):
        for i, bot in enumerate(self.__bots):
            print(f"{i}: {self.__bots[bot]} ({bot})")

    @property
    def bot(self):
        return self.__current_bot
    
    @bot.setter
    def bot(self, bot):
        try:
            botIndex = int(bot)
            self.__current_bot = list(self.__bots.keys())[botIndex]
        except ValueError:
            if bot in self.__bots:
                self.__current_bot = bot
            else:
                raise ValueError("Invalid bot name or index")
    
    def set_bot(self, bot):
        self.bot = bot

    def purge_conversation(self):
        self.__client.send_chat_break(self.__current_bot)

    def send_message_generator(self, message):
        for chunk in self.__client.send_message(self.__current_bot, message):
            yield chunk["text_new"]

    def send_message(self, message) -> str:
        return self.__client.send_message(self.__current_bot, message)["text"]
        