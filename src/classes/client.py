"""Модуль кастомного клиента"""

import datetime
import inspect
import io
import logging
import os
import time
import traceback
from typing import Any, Callable, List, Optional, Self, Tuple, TypeVar

from pyrogram import filters
from pyrogram.client import Client
from pyrogram.handlers.callback_query_handler import CallbackQueryHandler
from pyrogram.handlers.message_handler import MessageHandler
from pyrogram.types import CallbackQuery, Message
from pyrogram.errors.exceptions.bad_request_400 import MessageNotModified
from src.classes.buttons_menu import ButtonsMenu
from src.classes.customtinkoffacquiringapclient import CustomTinkoffAcquiringAPIClient
from src.classes.database import Database
from src.utils import Utils

ClientVar = TypeVar("ClientVar")


class CustomClient(Client):
    """Кастомный класс клиента"""

    def __init__(
        self,
        name: str = "bot",
        api_id: Optional[str | int] = None,
        api_hash: Optional[str] = None,
        bot_token: Optional[str] = None,
    ):
        # Настройка логгера
        self.logger = logging.getLogger("pyrobot")
        self.logger.setLevel(logging.DEBUG)

        # Добавление обработчика для записи в файл
        file_handler = logging.FileHandler("bot.log")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(file_handler)

        self.logger.info("Инициализация CustomClient...")

        try:
            self.db = Database()
            self.logger.debug("База данных успешно инициализирована")

            self.tb = CustomTinkoffAcquiringAPIClient(
                os.getenv("TINKOFF_TERMINAL_KEY"), os.getenv("TINKOFF_SECRET_KEY")
            )
            self.logger.debug("Клиент Tinkoff API успешно инициализирован")

            self.messages: dict[int | str, str] = {}

            if not self.check_args(api_id, api_hash, name, bot_token):
                self.logger.error("Проверка аргументов не пройдена")
                return

            self.logger.info("Проверка аргументов прошла успешно")

            super().__init__(
                name,
                api_id,
                api_hash,
                bot_token=bot_token,
            )

            self.setup_handlers()
            self.setup_callbacks()
            self.logger.info("Настройка клиента завершена успешно")

        except Exception as e:
            self.logger.critical(
                f"Ошибка при инициализации клиента: {str(e)}", exc_info=True
            )
            raise

    def check_args(
        self,
        api_id: Optional[str | int],
        api_hash: Optional[str],
        name: Optional[str],
        bot_token: Optional[str],
    ) -> bool:
        """Проверка аргументов."""
        self.logger.debug("Начало проверки аргументов")

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
            error_msg = (
                f"Отсутствуют обязательные параметры: {', '.join(missing_params)}"
            )
            self.logger.error(error_msg)
            raise ValueError(
                f"{error_msg}.\n"
                "Укажите их в файле .env. Пример конфигурации:\n\n"
                "API_ID = 12345678\n"
                "API_HASH = 0123456789abcdef0123456789abcdef\n"
                "NAME = ИМЯ_БОТА\n"
                "BOT_TOKEN = 0123456789abcdef0123456789abcdef\n\n"
                "API_ID и API_HASH можно получить на https://my.telegram.org/apps, "
                "а токен бота - у @BotFather."
            )

        self.logger.debug("Проверка аргументов успешно завершена")
        return True

    def get_functions(self):
        """Получение всех функций"""
        self.logger.debug("Получение списка функций клиента")

        try:
            super_functions = [name for name, _ in super().__class__.__dict__.items()]
            self_functions: List[Tuple[str, Callable[..., Any]]] = [
                (name, func)
                for name, func in self.__class__.__dict__.items()
                if inspect.iscoroutinefunction(func) and name not in super_functions
            ]

            self.logger.debug(
                f"Найдено {len(super_functions)} супер-функций и {len(self_functions)} пользовательских функций"
            )
            return super_functions, self_functions

        except Exception as e:
            self.logger.error(f"Ошибка при получении функций: {str(e)}", exc_info=True)
            raise

    def error_decorator(self, func: Callable[..., Any]):
        """Декоратор для обработки ошибок"""
        self.logger.debug(f"Создание декоратора ошибок для функции {func.__name__}")

        async def wrapper(*args, **kwargs):
            try:
                self.logger.debug(f"Вызов функции {func.__name__}")
                return await func(*args, **kwargs)
            except Exception as e:
                error_msg = f"Ошибка в {func.__name__}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                await self.error_handler(e, f"Ошибка в {func.__name__}")

        return wrapper

    def setup_callbacks(self):
        """Настройка прослушивания колбеков с обработкой ошибок"""
        self.logger.info("Настройка обработчиков колбеков...")

        try:
            wrapped_callback = self.error_decorator(self.callbacks)
            self.add_handler(CallbackQueryHandler(wrapped_callback, filters.all))
            self.logger.debug("Обработчик колбеков успешно добавлен")
        except Exception as e:
            self.logger.error(f"Ошибка при настройке колбеков: {str(e)}", exc_info=True)
            raise

    def setup_handlers(self):
        """Настройка хендлеров с автоматической обработкой ошибок"""
        self.logger.info("Настройка обработчиков сообщений...")

        try:
            _, self_functions = self.get_functions()

            for name, func in self_functions:
                if name.startswith("handle_"):
                    commands = name[7:].split("_")
                    _filters = filters.command(commands)

                    if "admin" in commands:
                        commands.remove("admin")
                        _filters = _filters & filters.user(Utils.ADMIN_IDS)

                    self.logger.debug(f"Добавление обработчика для команды: {commands}")

                    wrapped_handler = self.error_decorator(func)
                    self.add_handler(MessageHandler(wrapped_handler, _filters))

            self.logger.info(f"Успешно добавлено {len(self_functions)} обработчиков")
        except Exception as e:
            self.logger.error(
                f"Ошибка при настройке обработчиков: {str(e)}", exc_info=True
            )
            raise

    async def handle_check_admin(self, message: Message):
        """Функция проверка кода"""
        self.logger.info(f"Обработка команды check_admin от {message.from_user.id}")

        try:
            code = message.command[1]
            self.logger.debug(f"Проверка кода: {code}")

            if self.db.check_registration_by_hash(code, is_active=True):
                self.logger.info(f"Код {code} действителен")
                await message.reply(Utils.TRUE_CODE)
                self.db.disable_visitor(code)
                self.logger.debug(f"Код {code} деактивирован")
            elif self.db.check_registration_by_hash(code):
                self.logger.warning(f"Код {code} уже использован")
                await message.reply(Utils.FALSE_CODE_ALREADY_USED)
            else:
                self.logger.warning(f"Неверный код: {code}")
                await message.reply(Utils.FALSE_CODE)

        except IndexError:
            self.logger.error("Не указан код для проверки")
            await message.reply("❌ Не указан код для проверки")
        except Exception as e:
            self.logger.error(f"Ошибка при проверке кода: {str(e)}", exc_info=True)
            await message.reply("❌ Произошла ошибка при проверке кода")

    async def handle_sendall_admin(self, message: Message):
        """Функция рассылки сообщений"""
        self.logger.info(f"Обработка команды sendall от {message.from_user.id}")

        try:
            answer = await message.ask(
                "Введите текст для рассылки или `выход` для отмены"
            )

            if answer.text.lower() == "выход":
                self.logger.info("Рассылка отменена пользователем")
                return

            self.logger.debug(f"Текст рассылки: {answer.content[:50]}...")

            await message.reply(
                f"Ваша рассылка выглядит вот так:\n\n```text\n{answer.content}```",
                reply_markup=ButtonsMenu.get_newsletter_markup(message.from_user.id),
            )

            self.messages[str(message.from_user.id)] = answer.content
            self.logger.info("Сообщение для рассылки сохранено")

        except Exception as e:
            self.logger.error(
                f"Ошибка при подготовке рассылки: {str(e)}", exc_info=True
            )
            await message.reply("❌ Произошла ошибка при подготовке рассылки")

    async def handle_main_start(self, message: Message):
        """Главная функция для команд `main|start`"""
        self.logger.info(f"Обработка команды start/main от {message.from_user.id}")

        try:
            # Логирование информации о пользователе
            user_info = f"{message.from_user.full_name} (ID: {message.from_user.id})"
            self.logger.debug(f"Пользователь: {user_info}")
            self.logger.debug(f"Аргументы команды: {message.command[1:]}")

            # Добавление пользователя в БД
            self.db.add_user(message.from_user.id)
            self.logger.debug(f"Пользователь {user_info} добавлен в базу данных")

            args = message.command[1:]

            # Обработка админских команд
            if args and message.from_user.id in Utils.ADMIN_IDS:
                self.logger.info(f"Админская команда от {user_info}")

                try:
                    code = args[0]
                    self.logger.debug(f"Проверка кода: {code}")

                    user = self.db.get_all_visitors(code)
                    self.logger.debug(f"Результат запроса к БД: {user}")

                    if user:
                        if not user[3]:
                            self.logger.warning(f"Код {code} уже использован")
                            await message.reply(Utils.FALSE_CODE_ALREADY_USED)
                            return

                        self.db.disable_visitor(user[2])
                        self.logger.info(f"Код {code} деактивирован")

                        await message.reply(Utils.TRUE_CODE)
                        await message.delete()
                    else:
                        self.logger.warning(f"Неверный код: {code}")
                        await message.reply(Utils.FALSE_CODE)

                except Exception as e:
                    self.logger.error(
                        f"Ошибка в админской команде: {str(e)}", exc_info=True
                    )
                    await message.reply(Utils.FALSE_CODE)
                return

            # Обычный ответ для пользователей
            await message.reply(
                Utils.START_MESSAGE,
                reply_markup=ButtonsMenu.get_start_markup(),
            )
            self.logger.debug("Стартовое сообщение отправлено")

        except Exception as e:
            self.logger.critical(
                f"Критическая ошибка в handle_main_start: {str(e)}", exc_info=True
            )
            try:
                await message.reply("Произошла ошибка. Пожалуйста, попробуйте позже.")
            except Exception as send_error:
                self.logger.error(
                    f"Не удалось отправить сообщение об ошибке: {str(send_error)}"
                )

    async def handle_genqr_admin(self, message: Message):
        """Генерация QR-кода"""
        self.logger.info(f"Генерация QR-кода по запросу от {message.from_user.id}")

        try:
            msg = await message.reply("Подождите, идёт генерация Вашего QR кода!")
            self.logger.debug("Начало генерации QR-кода")

            image = await Utils.gen_qr_code(message.command[1:])
            self.logger.debug("QR-код сгенерирован")

            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format="PNG")
            img_byte_arr.seek(0)

            await msg.delete()
            await message.reply_photo(photo=img_byte_arr, caption="Вот Ваш QR!")
            self.logger.info("QR-код успешно отправлен")

        except Exception as e:
            self.logger.error(f"Ошибка при генерации QR-кода: {str(e)}", exc_info=True)
            await message.reply("❌ Произошла ошибка при генерации QR-кода")

    async def handle_addevent_admin(self, message: Message):
        """Добавление события"""
        self.logger.info(f"Добавление события по запросу от {message.from_user.id}")

        try:
            answer1 = await message.ask(
                f"**Введите дату дискотеки в формате** `{Utils.DATE_FORMAT}`"
            )

            date = datetime.datetime.strptime(answer1.content, Utils.DATE_FORMAT)
            self.logger.debug(f"Получена дата: {date}")

            answer2 = await message.ask(
                "**Введите числом максимальное количество пользователей или напишите**"
                "`выход` **для окончания создания события(стандратное число 250)**"
            )

            max_visitors = (
                int(answer2.content) if answer2.content.lower() != "выход" else 250
            )
            self.logger.debug(f"Максимальное количество посетителей: {max_visitors}")

            self.db.add_event(date, max_visitors)
            self.logger.info(f"Событие на {date} успешно добавлено")

        except ValueError:
            self.logger.error("Неверный формат даты")
            await message.reply(
                f"❌ Неверный формат даты. Используйте `{Utils.DATE_FORMAT}`"
            )
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении события: {str(e)}", exc_info=True)
            await message.reply("❌ Произошла ошибка при добавлении события")

    async def handle_delevent_admin(self, message: Message):
        """Удаление события"""
        self.logger.info(f"Удаление события по запросу от {message.from_user.id}")

        try:
            answer1 = await message.ask(
                "**Введите дату дискотеки которую хотите удалить в формате**"
                f"`{Utils.DATE_FORMAT}` или напишите `выход` для отмены"
            )

            if answer1.content.lower() == "выход":
                text = "**Удаление события отменено!**"
                self.logger.info("Удаление события отменено пользователем")
            else:
                date = datetime.datetime.strptime(answer1.content, Utils.DATE_FORMAT)
                self.db.delete_event(date)
                text = f"**Событие** __{date}__ **успешно удалено!**"
                self.logger.info(f"Событие на {date} успешно удалено")

            await answer1.reply(text)

        except ValueError:
            self.logger.error("Неверный формат даты")
            await message.reply(
                f"❌ Неверный формат даты. Используйте `{Utils.DATE_FORMAT}`"
            )
        except Exception as e:
            self.logger.error(f"Ошибка при удалении события: {str(e)}", exc_info=True)
            await message.reply("❌ Произошла ошибка при удалении события")

    async def error_handler(self, error: Exception, context: str = ""):
        """Асинхронный обработчик ошибок"""
        error_msg = "⚠️ **Ошибка в боте** ⚠️\n\n"
        if context:
            error_msg += f"**Контекст:** `{context}`\n\n"
        error_msg += f"**Тип ошибки:** `{type(error).__name__}`\n"
        error_msg += f"**Описание:** `{str(error)}`\n\n"

        traceback_msg = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        if len(traceback_msg) > 3000:
            traceback_msg = traceback_msg[:1500] + "\n...\n" + traceback_msg[-1500:]

        error_msg += f"```python\n{traceback_msg}\n```"

        self.logger.error(f"Ошибка: {context}\n{str(error)}\n{traceback_msg}")

        try:
            for admin in Utils.ADMIN_IDS:
                await self.send_message(admin, error_msg)
                self.logger.debug(f"Сообщение об ошибке отправлено админу {admin}")
        except Exception as e:
            self.logger.error(
                f"Ошибка при отправке сообщения об ошибке: {str(e)}", exc_info=True
            )

    async def callbacks(self, _: Client, query: CallbackQuery):
        """Функция приёма колбеков"""
        self.logger.info(f"Обработка callback от {query.from_user.id}: {query.data}")

        try:
            data = str(query.data)
            message = query.message
            user_info = f"{query.from_user.full_name} (ID: {query.from_user.id})"

            self.db.add_user(query.from_user.id)
            # self.logger.debug(f"Пользователь {user_info} добавлен/обновлен в БД")

            if data.startswith("send"):
                self.logger.info("Обработка callback для рассылки")
                tg_id = data.split("_")[1]

                if tg_id == "cancel":
                    await message.reply("Рассылка отменена")
                    await message.delete()
                    self.logger.info("Рассылка отменена пользователем")
                    return

                users = self.db.get_all_users()
                self.logger.debug(f"Найдено {len(users)} пользователей для рассылки")

                msg = await message.reply(
                    f"Рассылка запущена для {len(users)} пользователей"
                )

                success = 0
                errors = 0
                for user in users:
                    try:
                        await self.send_message(user[1], self.messages[tg_id])
                        success += 1
                    except Exception as e:
                        errors += 1
                        self.logger.warning(
                            f"Не удалось отправить сообщение пользователю {user[1]}: {str(e)}"
                        )

                await msg.edit_text(
                    f"Завершена рассылка для {len(users)} пользователей\n"
                    f"Успешно: {success}, Ошибок: {errors}"
                )

                await message.delete()
                self.logger.info(
                    f"Рассылка завершена. Успешно: {success}, Ошибок: {errors}"
                )

            elif data.startswith("useragreement"):
                self.logger.debug("Пользователь запросил пользовательское соглашение")
                await message.edit_text(
                    open("USER_AGREEMENT.txt", "r", encoding="utf-8").read(),
                    reply_markup=ButtonsMenu.get_menu_markup(),
                )

            elif data.startswith("reg_error"):
                self.logger.warning("Попытка регистрации на недоступное событие")
                await query.answer("❌ Это событие закончилось или места кончились")

            elif data.startswith("buytickets"):
                self.logger.info(f"Пользователь {user_info} покупает билеты...")
                await message.edit_reply_markup(
                    ButtonsMenu.get_buy_markup(query.from_user.id)
                )

            elif data.startswith("menu"):
                self.logger.debug("Возврат в главное меню")
                await message.edit_text(Utils.START_MESSAGE)
                await message.edit_reply_markup(ButtonsMenu.get_start_markup())

            elif data.startswith("reg_user_to"):
                self.logger.info(f"Регистрация пользователя {user_info} на событие")

                date_str = "".join(data.split("_")[3:])
                date = datetime.datetime.strptime(date_str, Utils.DATE_FORMAT)
                self.logger.debug(f"Дата события: {date}")

                # Проверка существующей регистрации
                result = self.db.check_registration_by_tgid(
                    query.from_user.id, date.date(), is_active=False
                )
                if result:
                    self.logger.warning(
                        f"Пользователь {query.from_bot.id} уже зарегистрирован на это событие"
                    )
                    await query.answer(
                        "❌ Вы уже были зарегистрированы на это событие!!!"
                    )
                    return

                if self.db.is_event_is_full(date):
                    self.logger.warning("Событие переполнено или завершено")
                    await query.answer("❌ Это событие закончилось или места кончились")
                    return

                cost = Utils.COST
                description = "Оплата прохода в клуб"
                self.logger.debug(f"Инициализация платежа на сумму {cost}")

                r = await self.tb.init_payment(
                    cost,
                    hash(query.from_user.id + time.time()),
                    description,
                )
                self.logger.debug(f"Платеж инициализирован, URL: {r['PaymentURL']}")

                await message.edit_text(
                    "Виды оплаты",
                    reply_markup=ButtonsMenu.get_payment_button(r["PaymentURL"], cost),
                )

                if await self.tb.await_payment(r["PaymentId"]):
                    self.logger.info(f"Платеж {r['PaymentId']} подтвержден")

                    try:
                        hash_code = self.db.reg_new_visitor(
                            query.from_user.id,
                            date,
                        )
                        self.logger.debug(f"Сгенерирован хэш-код: {hash_code}")
                    except AttributeError:
                        self.logger.warning("Пользователь уже зарегистрирован")
                        await message.edit_text(
                            "`❌ Вы уже зарегистрированы на это событие!!!`",
                        )
                        return

                    image = await Utils.gen_qr_code(
                        f"https://t.me/{self.me.username}?start={hash_code}"
                    )
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format="PNG")
                    img_byte_arr.seek(0)

                    await message.reply_photo(
                        photo=img_byte_arr,
                        caption=f"Ваш QR на дискотеку "
                        f"{date_str}!\n\n\n__Резервный код__:\n`{hash_code}`",
                    )
                    self.logger.info("QR-код успешно отправлен пользователю")

        except MessageNotModified:
            self.logger.debug("Сообщение не требует изменений")
        except Exception as e:
            self.logger.error(f"Ошибка в обработчике callback: {str(e)}", exc_info=True)
            try:
                await query.answer("❌ Произошла ошибка, попробуйте позже")
            except:
                pass
