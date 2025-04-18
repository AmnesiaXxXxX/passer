"""Главный модуль"""

import logging
import os

from dotenv import load_dotenv

from src.classes.client import CustomClient as CClient
from src.logger import setup_logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("tinkoff_acquiring.client").level = logging.ERROR
logging.getLogger("httpx").level = logging.ERROR
setup_logging()
load_dotenv(".env", override=True)
NAME = os.getenv("NAME", "bot")
API_ID = os.getenv("API_ID", None)
API_HASH = os.getenv("API_HASH", None)
BOT_TOKEN = os.getenv("BOT_TOKEN", None)

app = CClient(NAME, API_ID, API_HASH, BOT_TOKEN)


if __name__ == "__main__":
    app.run()
