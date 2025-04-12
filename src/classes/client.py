"""Модуль кастомного клиента"""

import datetime
import inspect
import io
import logging
import os
import time
from typing import Any, Callable, Coroutine, List, Optional, Tuple

from pyrogram import filters
from pyrogram.client import Client
from pyrogram.handlers.callback_query_handler import CallbackQueryHandler
from pyrogram.handlers.message_handler import MessageHandler
from pyrogram.types import CallbackQuery, Message

from classes.buttons_menu import Buttons_Menu
from classes.customtinkoffacquiringapclient import CustomTinkoffAcquiringAPIClient
from classes.database import Database
from utils import Utils


class CustomClient(Client):
    """Кастомный класс клиента"""

    def __init__(
        self,
        name: Optional[str] = "bot",
        api_id: Optional[str | int] = None,
        api_hash: Optional[str] = None,
        bot_token: Optional[str] = None,
    ):
        global print
        self.logger = logging.getLogger("pyrobot")
        self.db = Database()
        self.tb = CustomTinkoffAcquiringAPIClient(
            os.getenv("TINKOFF_TERMINAL_KEY"), os.getenv("TINKOFF_SECRET_KEY")
        )

        if not self.check_args(api_id, api_hash, name, bot_token):
            return
        print = self.logger.info
        logging.info("Проверка аргументов прошла успешно")

        # trunk-ignore(bandit/B101)
        assert name is not None, "name must not be None"
        super().__init__(name, api_id, api_hash, bot_token=bot_token, workers=24)
        self.setup_handlers()
        self.setup_callbacks()

    def check_args(
        self,
        api_id: Optional[str | int],
        api_hash: Optional[str],
        name: Optional[str],
        bot_token: Optional[str],
    ) -> bool:
        """Проверка аргументов.

        Если один или несколько обязательных параметров отсутствуют, возбуждается ValueError с перечислением недостающих параметров.
        """
        missing_params: List[str] = []
        if api_id is None:
            missing_params.append("API_ID")
        if api_hash is None:
            missing_params.append("API_HASH")
        if name is None:
            missing_params.append("NAME")
        if bot_token is None:
            missing_params.append("BOT_TOKEN")

        if missing_params:
            raise ValueError(
                f"Отсутствуют обязательные параметры: {', '.join(missing_params)}.\n"
                "Укажите их в файле .env. Пример конфигурации:\n\n"
                "API_ID = 12345678\n"
                "API_HASH = 0123456789abcdef0123456789abcdef\n"
                "NAME = ИМЯ_БОТА\n"
                "BOT_TOKEN = 0123456789abcdef0123456789abcdef\n\n"
                "API_ID и API_HASH можно получить на https://my.telegram.org/apps, "
                "а токен бота - у @BotFather."
            )
        return True

    def get_functions(self):
        super_functions = [name for name, _ in super().__class__.__dict__.items()]
        self_functions: List[Tuple[str, Callable[..., Any]]] = [
            (name, func)
            for name, func in self.__class__.__dict__.items()
            if inspect.iscoroutinefunction(func) and name not in super_functions
        ]
        return super_functions, self_functions

    def setup_callbacks(self):
        self.add_handler(CallbackQueryHandler(self.callbacks, filters.all))

    def setup_handlers(self):
        """Настройка хендлеров отслеживания сообщений"""
        _, self_functions = self.get_functions()

        for name, func in self_functions:
            if name.startswith("handle_"):
                commands: list[str] = name[7:].split("_")
                _filters = filters.command(commands)
                if "admin" in commands:
                    commands.remove("admin")
                    _filters = _filters & filters.user(Utils.ADMIN_IDS)
                self.logger.info(commands)
                self.add_handler(MessageHandler(func, _filters))

        self.logger.info(
            "Найдены асинхронные функции: \n%s",
            "\n".join([name for name, _ in self_functions]),
        )

    async def handle_main_start_help(self, message: Message):
        """Главная функция для команд `main|start|help`"""
        args = message.command[1:]
        if args and message.from_user.id in Utils.ADMIN_IDS:
            user = self.db.get_all_visitors(args[0])
            if user:
                self.db.delete_visitor(user[0], user[1])
                await message.delete()
            return
        await message.reply(Utils.START_MESSAGE, reply_markup=Buttons_Menu.get(0))

    async def handle_genqr_admin(self, message: Message):
        """Главная функция для команд `genqr`"""
        msg = await message.reply("Подождите, идёт генерация Вашего QR кода!")
        image = await Utils.genQRCode(message.command[1:])
        await msg.delete()
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)
        await message.reply_photo(photo=img_byte_arr, caption="Вот Ваш QR!")

    async def callbacks(self, client: Client, query: CallbackQuery):
        data = str(query.data)
        print(data)
        if data.startswith("reg_user_to"):
            cost = 200
            r = await self.tb.init_payment(
                cost,
                hash(query.from_user.id + time.time()),
                "Оплата прохода в клуб",
            )

            msg = await client.send_message(
                query.from_user.id,
                "Виды оплаты",
                reply_markup=Buttons_Menu.get_payment_button(r["PaymentURL"], cost),
            )
            if await self.tb.await_payment(r["PaymentId"]):
                hash_code = self.db.reg_new_visitor(
                    query.from_user.id,
                    datetime.datetime.strptime(
                        "".join(data.split("_")[3:]), Utils.DATE_FORMAT
                    ),
                )
                msg = await client.send_message(
                    query.from_user.id, "Подождите, идёт генерация Вашего QR кода!"
                )
                image = await Utils.genQRCode(
                    f"https://t.me/{self.me.username}?start={hash_code}"
                )
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format="PNG")
                img_byte_arr.seek(0)
                await msg.reply_photo(photo=img_byte_arr, caption="Вот Ваш QR!")
                await client.delete_messages(chat_id=msg.chat.id, message_ids=msg.id)
            else:
                await msg.edit_text("Оплата отклонена, попробуйте позже")

    def run(self, coroutine: Optional[Coroutine[Any, Any, Any]] = None) -> None:
        """Запуск клиента"""
        self.logger.info(f"Старт бота в {datetime.datetime.now(datetime.UTC)}")
        super().run(coroutine)
