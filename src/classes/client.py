"""Модуль кастомного клиента"""

import datetime
import logging
from typing import Any, Optional, Coroutine

from pyrogram.client import Client


class CustomClient(Client):
    """Кастомный класс клиента"""

    def __init__(
        self,
        name: str | None = "bot",
        api_id: Optional[str | int] = None,
        api_hash: Optional[str] = None,
        bot_token: Optional[str] = None,
    ):
        self.logger = logging.getLogger("pyrobot")
        if not self.check_args(api_id, api_hash, name, bot_token):
            return
        logging.info("Проверка аргументов прошла успешно")
        super().__init__(name, api_id, api_hash)

    def check_args(self, api_id, api_hash, name, bot_token):
        """Проверка аргументов"""
        if (api_id is None) or (api_hash is None):
            raise ValueError(
                """В .env файле нужно указать api_id и api_hash 
                                
                   Пример:
                                API_ID = 12345678 
                                API_HASH = 0123456789abcdef0123456789abcdef
                                
                   Их можно получить в `https://my.telegram.org/apps`
                             """
            )
        if name is None:
            raise ValueError(
                """В .env файле нужно указать имя сессии
                                
                   Пример:
                                NAME = ИМЯ_БОТА
                             """
            )
        if bot_token is None:
            raise ValueError(
                """В .env файле нужно указать токен бота
                                
                   Пример:
                                BOT_TOKEN = 0123456789abcdef0123456789abcdef
                             """
            )
        return True

    def run(self, coroutine: Optional[Coroutine[Any, Any, Any]] = None) -> None:
        """Запуск клиента"""
        self.logger.info(f"Старт бота в {datetime.datetime.now(datetime.UTC)}")
        super().run(coroutine)
