import inspect
import os
from datetime import date

from singleton import Singleton


def strftime(format):
    return date.today().strftime(format)


@Singleton
class _Logger:
    def __init__(self) -> None:
        # if not os.path.isdir("logs"):
        #    os.mkdir("logs")
        # date = strftime("%Y-%m-%d")
        # self.__file = open(f"logs/poe_client-{date}.log", "a")
        self.__file = open("client_poe.log", "a")

    def __del__(self):
        self.__file.close()

    def __call__(self, message):
        try:
            python_inspect = inspect.stack()[1]
            python_filename = python_inspect.filename.split("/")[-1]
            python_line = python_inspect.lineno
            python_function = python_inspect.function
            if type(message) == list:
                message = "\n".join(message)
            self.__file.write(
                f"[{strftime('%Y-%m-%d %H:%M:%S')}] \
            <{python_filename}|{python_function}|{python_line}>\n{message}\n"
            )
            self.__file.flush()
        except Exception as e:
            if hasattr(message, "__repr__"):
                self.__call__(message.__repr__())
            elif hasattr(message, "__str__"):
                self.__call__(message.__str__())
            else:
                self.__call__(f"<!>(no __repr__ or __str__ method found) {e}")


def Logger(message: str):
    _Logger(message)
