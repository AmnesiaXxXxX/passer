"""Главный модуль"""

import logging
import os

from dotenv import load_dotenv

from classes.client import CustomClient as Client

logging.basicConfig(level=logging.INFO)
logging.getLogger("tinkoff_acquiring.client").level = logging.ERROR

load_dotenv(override=True)
NAME = os.getenv("NAME", None)
API_ID = os.getenv("API_ID", None)
API_HASH = os.getenv("API_HASH", None)
BOT_TOKEN = os.getenv("BOT_TOKEN", None)


app = Client(NAME, API_ID, API_HASH, BOT_TOKEN)


if __name__ == "__main__":
    app.run()
