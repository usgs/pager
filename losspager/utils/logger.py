#!/usr/bin/python

# stdlib imports
import logging
from logging import StreamHandler, FileHandler
from logging.handlers import (SMTPHandler, TimedRotatingFileHandler)


class PagerLogger(object):
    def __init__(self, logfile, developers,
                 from_address, mail_host, debug=False):
        self._fmt = '%(levelname)s -- %(asctime)s -- %(module)s.%(funcName)s -- %(message)s'
        self._datefmt = '%Y-%m-%d %H:%M:%S'
        self._level = logging.DEBUG

        self._formatter = logging.Formatter(self._fmt, self._datefmt)

        # turn this on only if debug is True
        self._stream_handler = StreamHandler()
        self._stream_handler.setFormatter(self._formatter)
        self._stream_handler.setLevel(self._level)

        # turn this on only if debug is False
        if mail_host is not None:
            self._mail_handler = SMTPHandler(mail_host, from_address,
                                             developers, 'PAGER Error')
            self._mail_handler.setFormatter(self._formatter)
            self._mail_handler.setLevel(logging.CRITICAL)

        # turn this on only if debug is False
        self._global_handler = TimedRotatingFileHandler(
            logfile, when='midnight')
        self._global_handler.setFormatter(self._formatter)
        self._global_handler.setLevel(self._level)

        # set up logger
        logging.captureWarnings(True)
        self._logger = logging.getLogger()
        self._logger.setLevel(self._level)
        if debug:
            self._logger.addHandler(self._stream_handler)
        else:
            if mail_host is not None:
                self._logger.addHandler(self._mail_handler)
            self._logger.addHandler(self._global_handler)

    def getLogger(self):
        return self._logger

    def setVersionHandler(self, filename):
        self._logger.removeHandler(self._global_handler)
        local_handler = FileHandler(filename)
        local_handler.setFormatter(self._formatter)
        local_handler.setLevel(self._level)
        self._logger.addHandler(local_handler)

    def close(self):
        for handler in self._logger.handlers:
            self._logger.removeHandler(handler)
        del self._logger
