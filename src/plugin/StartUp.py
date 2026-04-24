import logging
from logging import Formatter
import os

from src.event.CalledMainEvent import CalledMainEvent
from src.manager.Events import _pendingInsts, EventListener

from src.protocol.ProgramProtocol import SAVED_DIR_PATH

class StartUp:
    @EventListener
    def onCalledMainEvent(self, _:CalledMainEvent) -> None:
        baseFormat = "%(asctime)s %(levelname)s %(name)s: %(message)s"
        class CFormartter(Formatter):
            FORMATS = {
                logging.ERROR: f"\033[41;37m{baseFormat}\033[0m",
                logging.WARNING: f"\033[33m{baseFormat}\033[0m",
                logging.DEBUG: baseFormat,
                logging.INFO: baseFormat
            }

            def format(self, record):
                log_fmt = self.FORMATS.get(record.levelno, "%(levelname)s: %(message)s")
                formatter = Formatter(log_fmt)
                return formatter.format(record)
        ch = logging.StreamHandler()
        ch.setFormatter(CFormartter())
        logging.basicConfig(
            level=logging.INFO,
            handlers=[ch]
        )
        os.makedirs(SAVED_DIR_PATH, exist_ok=True)

_pendingInsts.append(StartUp())