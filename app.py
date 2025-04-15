"""Главный модуль"""

import logging
import os

from dotenv import load_dotenv

from src.classes.client import CustomClient as Client
from src.logger import setup_logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("tinkoff_acquiring.client").level = logging.ERROR
setup_logging()
load_dotenv(override=True)
NAME = os.getenv("NAME", "bot")
API_ID = os.getenv("API_ID", None)
API_HASH = os.getenv("API_HASH", None)
BOT_TOKEN = os.getenv("BOT_TOKEN", None)

print(API_ID, API_HASH)
app = Client(NAME, API_ID, API_HASH, BOT_TOKEN)


if __name__ == "__main__":
    app.run()
