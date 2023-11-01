import logging
import sys

import colorlog

__loger__name__ = 'RulesTrackerPF'

# Создаем объект логгера с именем '__loger__name__'
logger = logging.getLogger(__loger__name__)

# Устанавливаем уровень логирования (раскомментируйте нужный уровень)
logger.setLevel(logging.DEBUG)

# Создаем и добавляем цветной обработчик для вывода логов в консоль
log_colors = {
    'DEBUG': 'green',
    'INFO': 'blue',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red,bg_white',
}
c_handler = logging.StreamHandler(sys.stdout)
c_format = '%(log_color)s[%(asctime)s.%(msecs)03d - %(funcName)23s() ] %(message)s'
c_format = colorlog.ColoredFormatter(c_format, log_colors=log_colors, datefmt='%d.%m.%Y %H:%M:%S')
c_handler.setFormatter(c_format)
logger.addHandler(c_handler)

# Создаем и добавляем обработчик для записи логов в файл '__loger__name__.log'
f_handler = logging.FileHandler(f'{__loger__name__}.log', mode='w', encoding='utf-8')
f_format = logging.Formatter(
    "[%(asctime)s.%(msecs)03d - %(funcName)23s() ] %(message)s", datefmt='%d.%m.%Y %H:%M:%S')
f_handler.setFormatter(f_format)
logger.addHandler(f_handler)
