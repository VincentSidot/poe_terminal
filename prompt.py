import argparse
import poe

from secret import TOKEN

class Command:
    def __init__(self, command, help_doc, args=None) -> None:
        self.__doc__ = help_doc
        self.__args__ = args
        self.command = command
        
    def __call__(self, args):
        return self.command(args)

class Prompt:
    __current_bot = None
    __bots = {}
    
    def arg_parser(self):
        parser = argparse.ArgumentParser(description="Poe.com api integration")
        parser.add_argument("-b", "--bot", help="Bot name", default="capybara")
        
        args = parser.parse_args()
        
        if args.bot:
            self.set_bot(args.bot)
    
    def __init__(self, token):
        self.client = poe.Client(token)
        self.__bots = self.client.bot_names
        self.__current_bot = list(self.__bots.keys())[0]

    def show_bots(self):
        for i, bot in enumerate(self.__bots):
            print(f"<{i}> {bot}: {self.__bots[bot]}")
        
    def set_bot(self, _input):
        try:
            index = int(_input)
            self.__current_bot = list(self.__bots.keys())[index]
        except ValueError:
            if _input in self.__bots:
                self.__current_bot = _input
            else:
                print("<!> Invalid bot name or index")
    
    def match_prompt(self, prompt):
        command = prompt[1:].split()[0]
        args = prompt[1:].split()[1:]
        commands = {
            "clear": Command(lambda _: self.client.send_chat_break(self.__current_bot), "Clear the chat"),
            "bots": Command(lambda _: self.show_bots(), "Show the list of bots"),
            "bot" : Command(lambda args: self.set_bot(args[0]), "Switch to another bot", "<botname|botid>"),
            "exit": Command(lambda _: exit(0), "Exit the program"),
            "help": Command(None, "Show this message"),
        }
        def help_message(_args):
            for command in commands:
                if commands[command].__args__ is None:
                    print(f"!{command} - {commands[command].__doc__}")
                else:
                    print(f"!{command} {commands[command].__args__} - {commands[command].__doc__}")
        commands["help"].command = help_message
        
        if command in commands:
            commands[command](args)
            return True
        else:
            print("<!> Invalid command (use !help for a list of commands)")
            return False

    
    def ask_prompt(self):
        prompt = input(f"({self.__bots[self.__current_bot]}) >> ")
        if prompt[0] == "!":
            self.match_prompt(prompt)
        else:
            for chunk in self.client.send_message(self.__current_bot, prompt):
                print(chunk["text_new"], end="", flush=True)
            print("\n", end="", flush=True)
    
    def run(self):
        while True:
            self.ask_prompt()


if __name__ == "__main__":
    client = Prompt(TOKEN)
    client.arg_parser()
    client.run()