import argparse
import readline
from rich.prompt import Prompt
from rich.console import Console
from singleton import Singleton
from poe_client import Poe

from secret import TOKEN

class Command:
    def __init__(self, command, help_doc, args=None) -> None:
        self.__doc__ = help_doc
        self.__args__ = args
        self.command = command
        
    def __call__(self, args):
        return self.command(args)

class CommandHandler:
    def __init__(self, commands=None) -> None:
        self.commands = {
            "help": Command(lambda _: self.__help__(), "Show this message"),
        }
        if commands is not None:
            self.commands.update(commands)
    
    def add_command(self, command, name, help_doc, args=None):
        self.commands[name] = Command(command, help_doc, args)
    
    def match_command(self, command):
        if command in self.commands:
            return self.commands[command]
        else:
            return Command(lambda _: print("<!> Invalid command (use !help for a list of commands)"), "Invalid command")
    
    def __help__(self):
        for command in self.commands:
            if self.commands[command].__args__ is None:
                print(f"!{command} - {self.commands[command].__doc__}")
            else:
                print(f"!{command} {self.commands[command].__args__} - {self.commands[command].__doc__}")

    def __getitem__(self, command):
        return self.match_command(command)

class Prompt:
    
    def __init__(self, token):
        self.__client = Poe(token)
        self.__commands = CommandHandler({
            "clear": Command(lambda _: self.__client.purge_conversation(), "Clear the chat"),
            "bots": Command(lambda _: self.__client.show_bots(), "Show the list of bots"),
            "bot": Command(lambda args: self.__client.set_bot(args[0]), "Switch to another bot", "<botname|botid>"),
            "exit": Command(lambda _: exit(0), "Exit the program"),
        })
    
    def arg_parser(self):
        parser = argparse.ArgumentParser(description="Poe.com api integration")
        parser.add_argument("-b", "--bot", help="Bot name", default="capybara")
        
        args = parser.parse_args()
        
        if args.bot:
            self.__client.bot = args.bot
    
    def match_prompt(self, prompt):
        command = prompt[1:].split()[0]
        args = prompt[1:].split()[1:]
        self.__commands[command](args)
    
    def ask_prompt(self):
        prompt = input(f"({self.__client.bot})> ")
        if prompt.startswith("!"):
            self.match_prompt(prompt)
        else:
            for chunk in self.__client.send_message_generator(prompt):
                print(chunk, end="", flush=True)
            print("")
    
    def run(self):
        while True:
            self.ask_prompt()


if __name__ == "__main__":
    client = Prompt(TOKEN)
    client.arg_parser()
    client.run()