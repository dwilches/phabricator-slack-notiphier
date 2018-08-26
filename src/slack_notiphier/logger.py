
import logging
from termcolor import colored

logging.basicConfig(level=logging.DEBUG, format='%(message)s')


class Logger(object):

    def __init__(self, class_name):
        self._logger = logging.getLogger(class_name)

    def debug(self, message, *args):
        self._logger.debug(colored(message.format(*args), 'green', attrs=['dark', 'bold']))

    def info(self, message, *args):
        self._logger.info(colored(message.format(*args), 'blue', attrs=['dark', 'bold']))

    def warn(self, message, *args):
        self._logger.warn(colored(message.format(*args), 'orange', attrs=['dark', 'bold']))

    def error(self, message, *args):
        self._logger.error(colored(message.format(*args), 'red', attrs=['dark', 'bold']))
