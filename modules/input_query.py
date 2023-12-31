import re
from colorama import Fore
import readline


def parse_search_query(query_string, commands):
    success = False
    pattern = re.compile(r'(\w+)([+=!])?=(\S+)')
    query_dict = {field: None for field in commands}

    matches = re.findall(pattern, query_string)
    for key, method, value in matches:
        method = method if method else '+'
        if key in query_dict:
            query_dict[key] = {'method': method, 'value': value}
            success = True
        else:
            print(f"{Fore.RED}Invalid key: {key}{Fore.RESET}")
            success = False

    return query_dict, success


def setup_readline(commands):
    readline.set_completer(QueryCompleter(commands).complete)
    # Регистрация клавиши `tab` для автодополнения
    readline.parse_and_bind('tab: complete')


class QueryCompleter:
    def __init__(self, options):
        self.matches = None
        self.options = sorted(options)

    def complete(self, text, state):
        if state == 0:
            # Создание списка соответствий.
            if text:
                self.matches = [s
                                for s in self.options
                                if s and s.startswith(text)]
            else:
                self.matches = self.options[:]
        # Вернуть элемент состояния из списка совпадений,
        # если их много.
        try:
            response = self.matches[state]
        except IndexError:
            response = None
        return response
