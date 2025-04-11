"""Модуль кастомного клиента"""

import datetime
import logging
from typing import Any, Callable, List, Optional, Coroutine, Self
import inspect
from pyrogram.client import Client
from pyrogram.handlers.message_handler import MessageHandler
from pyrogram import filters

class CustomClient(Client):
    """Кастомный класс клиента"""

    def __init__(
        self,
        name: Optional[str] = "bot",
        api_id: Optional[str | int] = None,
        api_hash: Optional[str] = None,
        bot_token: Optional[str] = None,
    ):
        self.logger = logging.getLogger("pyrobot")
        if not self.check_args(api_id, api_hash, name, bot_token):
            return

        logging.info("Проверка аргументов прошла успешно")
        super().__init__(name, api_id, api_hash)

    def check_args(self, api_id: Optional[str | int], api_hash: Optional[str], name: Optional[str], bot_token: Optional[str]) -> bool:
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

    def setup_handlers(self):
        """Настройка хендлеров отслеживания сообщений"""
        super_functions = [name for name, _ in super().__class__.__dict__.items()]
        async_functions: List[Callable[..., Any]] = []
        for name, func in self.__class__.__dict__.items():
            if inspect.iscoroutinefunction(func) and name not in super_functions:
                if name.startswith("handle_"):
                    
                    self.add_handler(MessageHandler(func, filters.command(name[8:].split("_"))))
                async_functions.append(func)
                
        self.logger.info(
            "Найдено асинхронных функций: %s",
            len([func.__name__ for func in async_functions]),
        )

    def run(self, coroutine: Optional[Coroutine[Any, Any, Any]] = None) -> None:
        """Запуск клиента"""
        self.logger.info(f"Старт бота в {datetime.datetime.now(datetime.UTC)}")
        self.setup_handlers()
        super().run(coroutine)
