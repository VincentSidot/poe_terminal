import argparse
import os
import sys
from typing import List

from prompt_toolkit import PromptSession  # type: ignore
from prompt_toolkit.completion import Completer, Completion  # type: ignore
from prompt_toolkit.key_binding import KeyBindings  # type: ignore
from rich.console import Console  # type: ignore
from rich.live import Live  # type: ignore
from rich.markdown import Markdown  # type: ignore

from logger import Logger
from poe_client import Poe, PoeError
from secret import TOKEN


class AutoCompletion(Completer):
    def __init__(self, commandHandler) -> None:
        self.__options = commandHandler

    def get_completions(self, document, complete_event):
        if not document.text.startswith("!"):
            return

        words = document.text.split()

        last_context = self.__options
        previous_word = words if document.text.endswith(" ") else words[:-1]
        try:
            if (
                previous_word[0] == self.__options.help
            ):  # Remove help command from previous_word list
                previous_word = previous_word[1:]
            if not previous_word[0].startswith("!"):
                previous_word[0] = "!" + previous_word[0]
        except IndexError:
            pass
        last_word = "" if document.text.endswith(" ") else words[-1]
        try:
            for word in previous_word:
                last_context = last_context[word].__args__
        except CommandError:
            return
        except KeyError:
            return  # No completion

        if last_context is None:  # No more arguments
            return
        if type(last_context) is str:  # Last argument is a string
            return
        # check if last_context is iterable
        for command in last_context:
            if command.startswith(last_word):
                yield Completion(
                    command,
                    start_position=-len(last_word),
                    display_meta=last_context[command].doc,
                )


class CommandError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class Command:
    def __init__(self, command, help_doc, args=None) -> None:
        self.__doc__ = help_doc
        self.__args__ = args
        self.command = command

    @property
    def doc(self):
        return self.__doc__

    def __str__(self):
        return f"{self.command=} | {self.doc=} | {self.args=}"

    @property
    def args(self):
        if self.__args__ is None:
            return ""
        if type(self.__args__) is str:
            return f"<{self.__args__}>"
        return f"<{'|'.join(command for command in self.__args__)}>"

    def __call__(self, args):
        try:
            return self.command(args)
        except PoeError as e:
            raise CommandError(e.message)
        except Exception as e:
            raise CommandError(f"<!> {e}")


class CommandHandler:
    def __init__(self, commands={}, separators=None, help=None) -> None:
        self.commands = commands
        self.__separators = separators
        self.__help = help
        if help is not None:
            self.commands.update(
                {help: Command(None, "Show this message", "command")})

    def __iter__(self):
        return iter(self.commands)

    @property
    def help(self):
        return self.__help

    def match_command(self, command):
        if command in self.commands:
            return self.commands[command]
        else:
            if self.__help is not None:
                raise CommandError(
                    f"Invalid command (use \
                    {self.__help} for a list of commands)"
                )
            else:
                raise CommandError("Invalid command")

    def __help__(self, commands):
        current_context = self
        try:
            """
            if commands is empty, it will raise an IndexError,
            and doesn't trigger the for loop
            """
            if not commands[0].startswith(
                "!"
            ):  # if command doesn't start with !, add it
                commands[0] = "!" + commands[0]
            for command in commands:
                temp = current_context[command].__args__
                if not (temp is None or type(temp) is str):
                    current_context = temp
                else:
                    break
        except IndexError:
            pass
        buffer = []
        for command in current_context:
            if current_context[command].__args__ is None:
                buffer.append(f"{' '.join(commands)} {command} \
                - {current_context[command].__doc__}")
            else:
                buffer.append(f"{' '.join(commands)} {command}\
                {current_context[command].args}\
                - {current_context[command].__doc__}")
        return "\n".join(buffer)

    def __getitem__(self, command):
        return self.match_command(command)

    def match_prompt(self, prompt):
        commands = prompt.split()
        if self.__help is not None and commands[0] == self.__help:
            return self.__help__(commands[1:])
        else:
            current_context = self
            for i, command in enumerate(commands):
                if current_context[commands[i]].command is not None:
                    return current_context[commands[i]](commands[i + 1:])
                current_context = current_context[command].__args__

    def __str__(self):
        return "\n".join(
            f"\t{command} - {self.commands[command]}" for command in self.commands
        )

    def match_token(self, prompt) -> str:
        Logger(f"CommandHandler.match_token({prompt})")
        result = self.match_prompt(prompt)
        if result is None:
            raise CommandError(f"No result returned with command '{prompt}'")
        if type(result) is tuple:
            return result[-1]
        else:
            try:
                return str(result)
            except Exception as e:
                raise CommandError(f"<!> {e}")

    def parse_token(self, prompt) -> str:
        Logger(f"CommandHandler.parse_token({prompt})")
        if self.__separators is None:
            return self.match_token(prompt)
        else:
            sub_prompt: List[str] = []
            new_prompt: List[str] = []
            is_in_token = False
            token_count = 0
            separator_begin = self.__separators[0]
            separator_end = self.__separators[1]
            for token in prompt.split():
                if token.startswith(separator_begin):
                    token_count += 1
                    is_in_token = True
                if token.endswith(separator_end):
                    token_count -= 1
                    if token_count == 0:
                        is_in_token = False
                        try:
                            new_prompt.append(
                                self.parse_token(" ".join(sub_prompt))
                            )
                        except CommandError as e:
                            raise CommandError(e.message)
                        finally:
                            sub_prompt = []
                if is_in_token:
                    sub_prompt.append(token)
                else:
                    new_prompt.append(token)

        return " ".join(new_prompt)

    def __call__(self, prompt) -> str:
        # return self.parse_token(prompt)
        temp = self.parse_token(prompt)
        Logger(f"CommandHandler.__call__({prompt}) -> {temp}")
        return temp


class Terminal:
    __modes = {"interactive": "Interactive mode", "batch": "Batch mode"}
    __mode = "interactive"
    __multiline = False
    __running = True

    def set_running(self, value: bool):
        self.__running = value

    def __init__(self, token):
        self.__client = Poe(token)
        self.__commands = CommandHandler(
            {
                "!clear": Command(
                    lambda _: (self.__client.send_chat_break(),
                               "Conversation cleared"),
                    "Clear the chat",
                ),
                "!set": Command(
                    None,
                    "Set value of prompt settings",
                    CommandHandler(
                        {
                            "bot": Command(
                                lambda args: (
                                    self.__client.set_bot(args[0]),
                                    f"Bot set to {args[0]}",
                                ),
                                "Switch to another bot",
                                CommandHandler(
                                    {
                                        str(bot): Command(None, self.__client.bots[bot])
                                        for bot in self.__client.bots
                                    }
                                ),
                            ),
                            "mode": Command(
                                lambda args: (
                                    self.set_mode(args[0]),
                                    f"Mode set to {args[0]}",
                                ),
                                "Switch to another mode",
                                CommandHandler(
                                    {
                                        mode: Command(None, self.__modes[mode])
                                        for mode in self.__modes
                                    }
                                ),
                            ),
                        }
                    ),
                ),
                "!list": Command(
                    None,
                    "List values of prompt settings",
                    CommandHandler(
                        {
                            "bot": Command(
                                lambda _: self.__client.show_bots(),
                                "Show the list of bots",
                            ),
                            "mode": Command(
                                lambda _: "\n".join(
                                    f"{mode} - {self.__modes[mode]}"
                                    for mode in self.__modes
                                ),
                                "Show the available modes",
                            ),
                        }
                    ),
                ),
                "!get": Command(
                    None,
                    "Get value of prompt settings",
                    CommandHandler(
                        {
                            "bot": Command(
                                lambda _: f"Current bot\
                                is {self.__client.bot}",
                                "Show the current bot",
                            ),
                            "mode": Command(
                                lambda _: f"Current mode is {self.__mode}",
                                "Show the current mode",
                            ),
                        }
                    ),
                ),
                "!exit": Command(
                    lambda _: (
                        self.set_running(False),
                        "[yellow] Exiting the program [/yellow]",
                    ), "Exit the program"
                ),
            },
            help="!help",
        )

        self.__token = CommandHandler(
            {
                "file": Command(
                    lambda args: self.__open_file(args[0]),
                    "Replace token by file content",
                    None
                ),
                "placeholder": Command(
                    lambda _: "Dummy placeholder",
                    "Dummy placeholder",
                    None
                )
            },
            separators=("{{", "}}")
        )

        self.__console = Console()
        self.__console.set_window_title("Poe.com terminal")

        bindings = KeyBindings()

        def prompt_continuation(width, _line_number, _is_soft_wrap):
            return "." * (width - 1) + " "

        # Add an additional key binding for toggling this flag.
        @bindings.add("f1")
        def _(event):
            "Run help command."
            event.app.current_buffer.insert_text(
                "!help", overwrite=True, move_cursor=True
            )
            event.app.current_buffer.validate_and_handle()

        @bindings.add("f2")
        def _(event):
            "Clear the console."
            event.app.current_buffer.insert_text(
                "!clear", overwrite=True, move_cursor=True
            )
            event.app.current_buffer.validate_and_handle()

        @bindings.add("f3")
        def _(event):
            "Exit the program."
            event.app.current_buffer.insert_text(
                "!exit", overwrite=True, move_cursor=True
            )
            event.app.current_buffer.validate_and_handle()

        @bindings.add("f4")
        def _(event):
            "Toggle multiline mode."
            self.__multiline = not self.__multiline
            self.__prompt.multiline = self.__multiline

        def bottom_toolbar():
            "Display the current input mode."
            text = f'Help: F1 | Clear: F2 | Exit: F3 | Multi-line ({self.__multiline}): F4'
            return [
                ("class:toolbar", text),
            ]

        def rprompt():
            return f"({self.__client.bot}|{self.__mode})"

        self.__prompt = PromptSession(
            completer=AutoCompletion(self.__commands),
            key_bindings=bindings,
            bottom_toolbar=bottom_toolbar,
            rprompt=rprompt,
            multiline=self.__multiline,
            vi_mode=True,
            prompt_continuation=prompt_continuation
        )

    def __open_file(self, file):
        try:
            with open(file, "r") as f:
                return f.read()
        except FileNotFoundError:
            raise CommandError(f"File {file} not found")
        except PermissionError:
            raise CommandError(f"Permission denied to file {file}")
        except Exception as e:
            raise CommandError(f"Error while opening file {file}: {e}")

    def set_mode(self, mode):
        self.__mode = mode

    def arg_parser(self):
        parser = argparse.ArgumentParser(description="Poe.com api integration")
        parser.add_argument("-b", "--bot", help="Bot name", default="capybara")
        parser.add_argument(
            "-m",
            "--mode",
            help="Mode",
            default="interactive",
            choices=["interactive", "batch", "debug"],
        )
        parser.add_argument(
            "--multiline",
            help="Multiline mode",
            action="store_true",
            default=False,
        )
        args = parser.parse_args()

        if args.bot:
            self.__client.bot = args.bot

        if args.mode:
            self.__mode = args.mode

        if args.multiline:
            self.__prompt.multiline = True

    def __ask_prompt(self):
        return self.__prompt.prompt("> ")

    def ask_prompt(self):
        prompt = self.__ask_prompt()
        self.__console.rule("", style="blue")
        try:
            if prompt.startswith("!"):
                self.__console.print(self.__commands(prompt))
            else:
                text = f" {prompt} --> {self.__token(prompt)}"
                if self.__mode == "interactive":
                    text_buffer = ""
                    with Live(
                        console=self.__console,
                        auto_refresh=False,
                        vertical_overflow="visible",
                    ) as live:
                        for text_chunk in self.__client.send_message_generator(text):
                            text_buffer += text_chunk
                            md = Markdown(text_buffer)
                            live.update(md)
                            if "\n" in text_chunk:
                                live.refresh()
                elif self.__mode == "batch":
                    md = Markdown(self.__client.send_message(text))
                    self.__console.print(md)
                elif self.__mode == "debug":
                    self.__console.print(text)
                else:
                    raise CommandError(f"Invalid mode '{self.__mode}'")
        except CommandError as e:
            self.__console.print(f"[red]{e}[/red]")
        finally:
            self.__console.rule("", style="blue")

    def run(self):
        while self.__running:
            self.ask_prompt()


if __name__ == "__main__":
    client = Terminal(TOKEN)
    client.arg_parser()
    client.run()
