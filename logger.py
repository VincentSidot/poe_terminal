import inspect
import os
from datetime import date

from singleton import Singleton


def strftime(format):
    return date.today().strftime(format)


@Singleton
class Logger:
    __file = None
    __is_active = False

    def __init__(self) -> None:
        # if not os.path.isdir("logs"):
        #    os.mkdir("logs")
        # date = strftime("%Y-%m-%d")
        # self.__file = open(f"logs/poe_client-{date}.log", "a")
        # self.__file = open("client_poe.log", "a")
        self.__file = open("client_poe.log", "w")

    def __del__(self):
        if self.__file is not None:
            self.__file.close()

    def set_file(self, file):
        if self.__file is not None:
            self.__file.close()
        self.__file = open(file, "w")

    def set_active(self, is_active):
        self.__is_active = is_active

    def get_active(self):
        return self.__is_active

    @property
    def is_active(self):
        return self.get_active()

    @is_active.setter
    def is_active(self, is_active):
        self.set_active(is_active)

    def __call__(self, message):
        if not self.__is_active:
            return
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
