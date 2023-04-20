from typing import Dict, Generator

import poe  # type: ignore

from logger import Logger


class PoeError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class Poe:
    __current_bot = None
    __bots: Dict[str, Dict[str, str]] = {}
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
        if self.__client is None:
            raise PoeError("Client is not initialized")
        self.__client.send_chat_break(self.__current_bot)
        return None

    def send_message_generator(self, message) -> Generator[str, None, None]:
        if self.__client is None:
            raise PoeError("Client is not initialized")
        Logger(f"Sent message: {message}")
        for chunk in self.__client.send_message(self.__current_bot, message):
            text = chunk["text_new"]
            Logger(f"Received chunks: {chunk}")
            yield text

    def send_message(self, message) -> str:
        if self.__client is None:
            raise PoeError("Client is not initialized")
        chunk = {"text": ""}
        for chunk in self.__client.send_message(self.__current_bot, message):
            pass
        Logger(f"Sent message: {message}\nReceived chunk: {chunk}")
        text = chunk["text"]
        return text


def max_prompt_len(client) -> int:
    prompt = "a"
    try:
        while True:
            client.send_message(prompt)
            prompt += "a"
    finally:
        return len(prompt)


def check_prompt_len(prompt_len) -> bool:
    client = Poe(token)
    try:
        prompt = "a" * prompt_len
        client.send_message(prompt)
        return True
    except:
        return False


def max_prompt_len_dicotomy(prompt_len_min, prompt_len_max) -> int:
    if not check_prompt_len(prompt_len_min):
        return prompt_len_min
    if not check_prompt_len(prompt_len_max):
        return max_prompt_len_dicotomy(prompt_len_min, (prompt_len_max + prompt_len_min) // 2)
    if check_prompt_len(prompt_len_max):
        raise Exception("Max prompt length is too low")
    return prompt_len_max


if __name__ == "__main__":
    from secret import TOKEN as token
    max_len = max_prompt_len_dicotomy(500, 100000)
    print(f"Max prompt length: {max_len}")
