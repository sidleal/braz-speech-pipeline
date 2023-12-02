import logging
from pathlib import Path
from datetime import datetime

LOGGING_FOLDER = Path("./logs")
LOGGING_FOLDER.mkdir(exist_ok=True, parents=True)
handler_file = logging.FileHandler(
    filename=LOGGING_FOLDER / f"{datetime.now()}.log",
    mode="a",
)


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "%(levelname)s %(asctime)s [%(filename)s:%(funcName)s:%(lineno)d] %(message)s"
    )
    handler_file.setFormatter(formatter)
    handler.setFormatter(formatter)

    handler.setLevel(logging.DEBUG)
    handler_file.setLevel(logging.DEBUG)

    logger.addHandler(handler_file)
    logger.addHandler(handler)

    return logger
