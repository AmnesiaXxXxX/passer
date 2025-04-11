"""Главный модуль"""

import os

from dotenv import load_dotenv

from classes.client import CustomClient as Client

load_dotenv()

API_ID = os.getenv("API_ID", None)
API_HASH = os.getenv("API_HASH", None)
BOT_TOKEN = os.getenv("BOT_TOKEN", None)


app = Client("bot", API_ID, API_HASH, BOT_TOKEN)


if __name__ == "__main__":
    app.run()