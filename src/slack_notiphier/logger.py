
import logging
from termcolor import colored

from .config import get_config


_valid_levels = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARN': logging.WARN,
    'ERROR': logging.ERROR,
}


def reload():
    _log_level = get_config('log_level', 'INFO')
    if _log_level not in _valid_levels:
        raise ValueError("Configured log level is not valid: " + _log_level)

    logging.basicConfig(level=_valid_levels[_log_level], format='%(message)s')


reload()


class Logger(object):

    def __init__(self, class_name):
        self._logger = logging.getLogger(class_name)

    def debug(self, message, *args):
        self._logger.debug(colored(message.format(*args), 'green', attrs=['dark', 'bold']))

    def info(self, message, *args):
        self._logger.info(colored(message.format(*args), 'blue', attrs=['dark', 'bold']))

    def warn(self, message, *args):
        self._logger.warn(colored(message.format(*args), 'yellow', attrs=['dark', 'bold']))

    def error(self, message, *args):
        self._logger.error(colored(message.format(*args), 'red', attrs=['dark', 'bold']))
