"""Модуль кастомного клиента с использованием SQLAlchemy"""

import asyncio
import datetime
import inspect
import io
import logging
import os
import queue
import threading
import time
import traceback
from typing import Callable, Optional, TypeVar

from pyrogram import filters
from pyrogram.client import Client
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import CallbackQuery, Message, User

from src.classes.buttons_menu import ButtonsMenu
from src.classes.customtinkoffacquiringapclient import CustomTinkoffAcquiringAPIClient
from src.classes.database import Database
from src.utils import Utils

ClientVar = TypeVar("ClientVar")


class CustomClient(Client):
    """Кастомный клиент с интеграцией SQLAlchemy и очередями"""

    def __init__(
        self,
        name: str = "bot",
        api_id: Optional[str | int] = None,
        api_hash: Optional[str] = None,
        bot_token: Optional[str] = None,
    ):
        self.logger = logging.getLogger("pyrobot")
        self.db = Database()
        self.tb = CustomTinkoffAcquiringAPIClient(
            os.getenv("TINKOFF_TERMINAL_KEY"), os.getenv("TINKOFF_SECRET_KEY")
        )
        self.messages: dict[str, str] = {}
        self.task_queue = queue.Queue()

        self._validate_credentials(api_id, api_hash, name, bot_token)
        super().__init__(
            name,
            api_id,
            api_hash,
            bot_token=bot_token,
            workers=int(os.getenv("WORKERS", 10)),
            max_concurrent_transmissions=int(
                os.getenv("MAX_CONCURRENT_TRANSMISSONS", 10)
            ),
        )

        self._setup_handlers()
        self._setup_callbacks()
        threading.Thread(target=self._worker, daemon=True).start()
        self.logger.info("Инициализация клиента завершена")

    def _worker(self):
        """Воркер для последовательной обработки задач из очереди"""
        while True:
            func, arg = self.task_queue.get()
            try:

                asyncio.run(func(*arg))
            except Exception as e:
                self.logger.error(f"Ошибка обработки задачи: {e}")
            finally:
                self.task_queue.task_done()

    def _validate_credentials(self, *args):
        """Проверка учетных данных"""
        required = {
            "API_ID": args[0],
            "API_HASH": args[1],
            "NAME": args[2],
            "BOT_TOKEN": args[3],
        }
        missing = [k for k, v in required.items() if v is None]

        if missing:
            raise ValueError(
                f"Отсутствуют обязательные параметры: {', '.join(missing)}\n\n"
                "Пример конфигурации .env:\n\n"
                "API_ID=12345678\n"
                "API_HASH=0123456789abcdef0123456789abcdef\n"
                "NAME=ИМЯ_БОТА\n"
                "BOT_TOKEN=0123456789abcdef0123456789abcdef"
            )

    def _setup_handlers(self):
        """Регистрация обработчиков команд"""
        for name in dir(self):
            if not name.startswith("handle_"):
                continue

            method = getattr(self, name)
            if inspect.iscoroutinefunction(method):
                commands = name[7:].split("_")
                if "admin" in commands:
                    commands.remove("admin")
                handler = self._wrap_handler(method, commands)
                self.add_handler(MessageHandler(handler, filters.command(commands)))

    def _setup_callbacks(self):
        """Регистрация обработчиков колбэков"""
        wrapped_callback = self._error_handler_wrapper(self._process_callback)
        self.add_handler(CallbackQueryHandler(wrapped_callback))

    def _wrap_handler(self, handler: Callable, commands: list) -> Callable:
        """Обертка для обработчиков с проверкой прав"""
        if "admin" in commands:
            handler = filters.user(Utils.ADMIN_IDS)
        return self._error_handler_wrapper(handler)

    def _error_handler_wrapper(self, func: Callable) -> Callable:
        """Декоратор для обработки ошибок"""

        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                await self._report_error(e, func.__name__)

        return wrapper

    async def _report_error(self, error: Exception, context: str = ""):
        """Отправка отчета об ошибке"""
        error_msg = (
            f"⚠️ **Ошибка в {context}** ⚠️\n\n"
            f"**Тип:** `{type(error).__name__}`\n"
            f"**Описание:** `{str(error)}`\n\n"
            f"```python {traceback.format_exc()[:3000]}\n```"
        )

        for admin_id in Utils.ADMIN_IDS:
            try:
                await self.send_message(admin_id, error_msg)
            except Exception as e:
                self.logger.error(f"Ошибка отправки сообщения: {e}")

    async def _process_message(self, client, message):
        """Обработка сообщения из очереди"""
        command = message.command[0]
        method_name = f"handle_{command}"

        if hasattr(self, method_name):
            await getattr(self, method_name)(client, message)

    async def handle_genqr_admin(self, _, message: Message):
        """Функция для генерации QR кода"""
        qr_image = await Utils.gen_qr_code(
            Utils.QR_URL(self.me.username if self.me else "", message.command[1])
        )

        with io.BytesIO() as buffer:
            qr_image.save(buffer, format="PNG")
            buffer.seek(0)
            await message.reply_photo(
                buffer,
                caption=Utils.TRUE_PROMPT.format(
                    message.command[2], message.command[1]
                ),
            )

    async def handle_check_admin(self, message: Message):
        """Проверка регистрации по хэш-коду (админ)"""
        if hash_code := message.command[1]:
            visitor = self.db.check_registration_by_hash(hash_code)
            if visitor:
                if bool(visitor.is_active):
                    await message.reply(Utils.TRUE_CODE)
                    self.db.disable_visitor(hash_code)
            else:
                await message.reply(Utils.FALSE_CODE)

    async def handle_sendall_admin(self, message: Message):
        """Рассылка сообщений (админ)"""
        answer = await message.ask("Введите текст рассылки или 'выход' для отмены")
        if answer.text.lower() != "выход":
            self.messages[str(message.from_user.id)] = answer.text
            await message.reply(
                f"Предпросмотр:\n\n{answer.text}",
                reply_markup=ButtonsMenu.get_newsletter_markup(message.from_user.id),
            )

    async def handle_getmyqr(self, _, message: Message):
        """Функция для генерации QR кода личного для пользователя"""
        args = message.command[1:]
        if len(args) > 0:
            if message.from_user.id in Utils.ADMIN_IDS:
                user_id = args[0]
            else:
                user_id = message.from_user.id
        else:
            user_id = message.from_user.id
        users = [
            event
            for event in self.db.get_all_visitors(user_id)
            if bool(event.to_datetime >= datetime.datetime.now().date())
        ]
        for user in users:

            qr_image = await Utils.gen_qr_code(
                Utils.QR_URL(self.me.username if self.me else "", message.command[1])
            )

            with io.BytesIO() as buffer:
                qr_image.save(buffer, format="PNG")
                buffer.seek(0)
                await message.reply_photo(
                    buffer,
                    caption=Utils.TRUE_PROMPT.format(user.to_datetime, user.hash_code),
                )

    async def handle_main_start(self, _: Client, message: Message):
        """Обработка команд /main и /start"""
        self.db.add_user(message.from_user.id)
        if len(message.command) > 1:
            hash_code = message.command[1]
            if hash_code.startswith("activate"):
                await message.delete()
                return
                # visitor = self.db.check_registration_by_hash(hash_code, False)
                # if visitor:
                #     self.db.enable_visitor(hash_code=hash_code)
                #     qr_image = await Utils.gen_qr_code(
                #         f"https://t.me/{self.me.username}?start={hash_code}"
                #     )

                #     with io.BytesIO() as buffer:
                #         qr_image.save(buffer, format="PNG")
                #         buffer.seek(0)
                #         await message.reply_photo(
                #             buffer,
                #             caption=Utils.TRUE_PROMPT.format(
                #                 visitor.to_datetime, hash_code
                #             ),
                #         )
                #     return
            else:
                if message.from_user.id in Utils.ADMIN_IDS:
                    if self.db.check_registration_by_hash(hash_code):
                        self.db.disable_visitor(hash_code)
                        await message.reply(Utils.TRUE_CODE)
                    else:
                        await message.reply(Utils.FALSE_CODE)
                    return

        await message.reply(
            Utils.START_MESSAGE, reply_markup=ButtonsMenu.get_start_markup()
        )

    async def handle_addevent_admin(self, _, message: Message):
        """Добавление нового события (админ)"""
        answer = await message.ask(f"Введите дату в формате {Utils.DATE_FORMAT}")
        event_date = datetime.datetime.strptime(answer.text, Utils.DATE_FORMAT).date()

        answer = await message.ask(
            "Введите максимальное количество участников (по умолчанию 250)"
        )
        max_visitors = int(answer.text) if answer.text.isdigit() else 250

        self.db.add_event(event_date, max_visitors)
        self.logger.info(
            f"Добавлено событие на {event_date} " f"(макс. участников: {max_visitors})"
        )

    async def _process_callback(self, _: Client, query: CallbackQuery):
        """Обработка callback-запросов"""
        data = str(query.data)
        message = query.message

        if data.startswith("useragreement"):
            await self._show_user_agreement(message)
        elif data.startswith("reg_error"):
            await self._process_registration_errors(query, message)
        elif data.startswith("reg_user_to"):
            await self._process_registration(query, message)
        elif data.startswith("buytickets"):
            await self._show_payment_options(message, query.from_user)
        elif data.startswith("menu"):
            await self._show_main_menu(message)
        elif data.startswith("send"):
            await self._process_newsletter(data, message)

    async def _process_registration_errors(self, query: CallbackQuery, _: Message):
        match query.data:
            case "reg_error_already_registrate":
                await query.answer(Utils.CALLBACK_USER_ALREADY_REGISTRATE)
            case "reg_error":
                await query.answer(Utils.CALLBACK_USER_NOT_AVAILABLE)
            case _:
                await query.answer("Произошла неизвестная ошибка")

    async def _process_registration(self, query: CallbackQuery, message: Message):
        """Обработка регистрации на событие"""
        to_datetime = datetime.datetime.strptime(
            str(query.data).rsplit("_", maxsplit=1)[-1], Utils.DATE_FORMAT
        ).date()

        if self.db.check_registration_by_tgid(query.from_user.id, to_datetime):
            await query.answer(Utils.CALLBACK_USER_ALREADY_REGISTRATE)
            return

        if self.db.is_event_full(to_datetime):
            await query.answer("❌ Нет свободных мест!")
            return
        hash_code = self.db.reg_new_visitor(
            query.from_user.id,
            datetime.datetime.combine(to_datetime, datetime.time()),
            False,
        )
        payment = await self.tb.init_payment(
            Utils.COST,
            f"{query.from_user.id}_{time.time()}",
            "Оплата входа на мероприятие",
            success_url=Utils.SUCCESS_URL(
                self.me.username if self.me else "", hash_code[:5]
            ),
        )

        await message.edit_text(
            "Выберите способ оплаты:",
            reply_markup=ButtonsMenu.get_payment_markup(
                payment["PaymentURL"], Utils.COST
            ),
        )

        if await self.tb.await_payment(payment["PaymentId"]):
            self.db.enable_visitor(hash_code=hash_code)

            qr_image = await Utils.gen_qr_code(
                Utils.QR_URL(self.me.username if self.me else "", hash_code)
            )

            with io.BytesIO() as buffer:
                qr_image.save(buffer, format="PNG")
                buffer.seek(0)
                await message.reply_photo(
                    buffer, caption=Utils.TRUE_PROMPT.format(to_datetime, hash_code)
                )
            return
        self.db.delete_visitor(query.from_user.id, to_datetime)
        return 
    async def _show_user_agreement(self, message: Message):
        """Отображение пользовательского соглашения"""
        await message.edit_text(
            open("USER_AGREEMENT.txt").read(),  # Полный текст соглашения
            reply_markup=ButtonsMenu.get_menu_markup(),
        )

    async def _show_payment_options(self, message: Message, user: User):
        """Отображение вариантов оплаты"""
        await message.edit_reply_markup(ButtonsMenu.get_buy_markup(user.id))

    async def _show_main_menu(self, message: Message):
        """Отображение главного меню"""
        await message.edit_text(
            Utils.START_MESSAGE, reply_markup=ButtonsMenu.get_start_markup()
        )

    async def _process_newsletter(self, data: str, message: Message):
        """Обработка рассылки сообщений"""
        user_id = data.split("_")[1]
        if user_id == "cancel":
            await message.delete()
            return

        users = [user.tg_id for user in self.db.get_all_users()]
        progress = await message.reply(f"Рассылка для {len(users)} пользователей...")

        for user_id in users:
            try:
                await self.send_message(
                    str(user_id), str(self.messages.__getitem__(str(user_id)))
                )
            except Exception as e:
                self.logger.error(f"Ошибка отправки для {user_id}: {e}")

        await progress.edit_text(f"Рассылка завершена ({len(users)} пользователей)")
        await message.delete()
