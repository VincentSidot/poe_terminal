from logger import Logger
from poe_client import PoeError

from typing import List


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
        return f'<{" | ".join(command for command in self.__args__)}>'

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
            and doesn"t trigger the for loop
            """
            if not commands[0].startswith(
                "!"
            ):  # if command doesn"t start with !, add it
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
                buffer.append(f'{" ".join(commands)} {command} \
                - {current_context[command].__doc__}')
            else:
                buffer.append(f'{" ".join(commands)} {command}\
                {current_context[command].args}\
                - {current_context[command].__doc__}')
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
            raise CommandError(f'No result returned with command "{prompt}"')
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
                            temp = []
                            temp.append(f"new_promp_before: {new_prompt}")
                            temp.append(f"sub_prompt: {sub_prompt}")
                            new_prompt.append(
                                self.parse_token(" ".join(sub_prompt)).strip()
                            )
                            temp.append(f"new_prompt_after: {new_prompt}")
                            Logger("\n".join(temp))
                        except CommandError as e:
                            raise CommandError(e.message)
                        finally:
                            sub_prompt = []
                elif is_in_token:
                    sub_prompt.append(token)
                else:
                    new_prompt.append(token)

        return " ".join(new_prompt)

    def __call__(self, prompt) -> str:
        return self.parse_token(prompt)


def run_test(n):
    command_handler = CommandHandler(
        {
            "test": Command(lambda _: "test_placeholder", "test command"),
            "test_with_args": Command(lambda args: f"test({args})", "test command with args"),
        },
        separators=["{{", "}}"],
    )

    input_texts = [
        "This is a test without placeholders",
        "This is a test with space escaped placeholder {{ test }}",
        "This is a test with non space escaped placeholder {{test}}",
    ]
    reference_texts = [
        "This is a test without placeholders",
        "This is a test with test_placeholder",
        "This is a test with test_placeholder",
    ]

    for i, item in enumerate(zip(input_texts, reference_texts)):
        if i >= n:
            break
        try:
            computed_text = command_handler(item[0])
            print(f"\"{item[0]}\" -> \"{computed_text}\" == \"{item[1]}\"")
            try:
                assert computed_text == item[1]
            except AssertionError:
                print(
                    f"\tAssertionError: \"{computed_text}\" != \"{item[1]}\"")
        except CommandError as e:
            print(f"CommandError: {e.message}")


if __name__ == "__main__":
    try:
        run_test(2)
    except Exception as e:
        print(e)
