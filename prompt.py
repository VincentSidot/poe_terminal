import argparse
import os
import sys
from typing import List

from prompt_toolkit import PromptSession, prompt  # type: ignore
from prompt_toolkit.completion import Completer, Completion  # type: ignore
from prompt_toolkit.key_binding import KeyBindings  # type: ignore
from rich.console import Console  # type: ignore
from rich.live import Live  # type: ignore
from rich.markdown import Markdown  # type: ignore

from command import Command, CommandError, CommandHandler  # type: ignore
from logger import Logger
from poe_client import Poe, PoeError


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


class Terminal:
    __modes = {"interactive": "Interactive mode", "batch": "Batch mode"}
    __mode = "interactive"
    __multiline = False
    __running = True
    __token = None

    def set_running(self, value: bool):
        self.__running = value

    def __init__(self):
        args = self.arg_parser()
        self.__client = Poe(args.token)
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
                    "file",
                ),
                "code": Command(
                    lambda args: f"\n```{args[0]}\n{self.__open_file(args[1])}\n```\n",
                    "Replace token by file content in a markdown code block",
                    "language file",
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

        if args.bot:
            self.__client.bot = args.bot

        if args.mode:
            self.__mode = args.mode

        if args.multiline:
            self.__prompt.multiline = True

        if args.log:
            Logger.is_active = True
            Logger.set_file(args.log)

    def __open_file(self, file):
        striped_file = file.replace("\"", "").replace("\'", "").strip()
        Logger(f"{os.getcwd()=}")
        Logger(f"{os.listdir()=}")
        Logger(f"{striped_file=}")
        try:
            with open(striped_file, "r") as f:
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
            choices=["interactive", "batch"],
        )
        parser.add_argument(
            "--multiline",
            help="Multiline mode",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "-l",
            "--log",
            type=str,
            help="Log file",
        )
        parser.add_argument(
            "-t", "--token", help="POE Token fetch from poe.com cookies", required=True)
        args = parser.parse_args()
        return args

    def __ask_prompt(self) -> str:
        prompt = self.__prompt.prompt("> ")
        Logger(f"{prompt=} | {len(prompt)=}")
        return prompt

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
    client = Terminal()
    client.run()
