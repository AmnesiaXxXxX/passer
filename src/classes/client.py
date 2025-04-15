"""Модуль кастомного клиента"""

import datetime
import inspect
import io
import logging
import os
import time
import traceback
from typing import Any, Callable, List, Optional, Tuple

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


class CustomClient(Client):
    """Кастомный класс клиента"""

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

        if not self.check_args(api_id, api_hash, name, bot_token):
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
        self.logger.info("Настройка прошла успешно")

    def check_args(
        self,
        api_id: Optional[str | int],
        api_hash: Optional[str],
        name: Optional[str],
        bot_token: Optional[str],
    ) -> bool:
        """Проверка аргументов.

        Если один или несколько обязательных параметров отсутствуют,
        возбуждается ValueError с перечислением недостающих параметров.
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
        """Получение всех функций"""

        super_functions = [name for name, _ in super().__class__.__dict__.items()]
        self_functions: List[Tuple[str, Callable[..., Any]]] = [
            (name, func)
            for name, func in self.__class__.__dict__.items()
            if inspect.iscoroutinefunction(func) and name not in super_functions
        ]
        return super_functions, self_functions

    def error_decorator(self, func: Callable) -> Callable:
        """Декоратор для обработки ошибок"""

        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                await self.error_handler(e, f"Ошибка в {func.__name__}")

        return wrapper

    def setup_callbacks(self):
        """Настройка прослушивания колбеков с обработкой ошибок"""
        wrapped_callback = self.error_decorator(self.callbacks)
        self.add_handler(CallbackQueryHandler(wrapped_callback, filters.all))

    def setup_handlers(self):
        """Настройка хендлеров с автоматической обработкой ошибок"""
        _, self_functions = self.get_functions()

        for name, func in self_functions:
            if name.startswith("handle_"):
                commands = name[7:].split("_")
                _filters = filters.command(commands)

                if "admin" in commands:
                    commands.remove("admin")
                    _filters = _filters & filters.user(Utils.ADMIN_IDS)

                # Оборачиваем обработчик в декоратор ошибок
                wrapped_handler = self.error_decorator(func)
                self.add_handler(MessageHandler(wrapped_handler, _filters))

    async def handle_check_admin(self, message: Message):
        """Функция проверка кода"""

        if self.db.check_registration_by_hash(message.command[1], is_active=True):
            await message.reply(Utils.TRUE_CODE)
            self.db.disable_visitor(message.command[1])
        elif self.db.check_registration_by_hash(message.command[1]):
            await message.reply(Utils.FALSE_CODE_ALREADY_USED)
        else:
            await message.reply(Utils.FALSE_CODE)

    async def handle_main_start(self, message: Message):
        """Главная функция для команд `main|start|help`"""
        args = message.command[1:]
        if args and message.from_user.id in Utils.ADMIN_IDS:
            try:
                user = self.db.get_all_visitors(args[0])[0]
                if user:
                    if not user[3]:
                        await message.reply(Utils.FALSE_CODE_ALREADY_USED)
                        return
                    self.db.disable_visitor(user[2])
                    await message.reply(Utils.TRUE_CODE)
                    await message.delete()
            except IndexError:
                await message.reply(Utils.FALSE_CODE)
            return
        await message.reply(
            Utils.START_MESSAGE,
            reply_markup=ButtonsMenu.get_start_markup(),
        )

    async def handle_genqr_admin(self, message: Message):
        """Главная функция для команд `genqr`"""
        msg = await message.reply("Подождите, идёт генерация Вашего QR кода!")
        image = await Utils.gen_qr_code(message.command[1:])
        await msg.delete()
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)
        await message.reply_photo(photo=img_byte_arr, caption="Вот Ваш QR!")

    async def handle_addevent_admin(self, message: Message):
        """Функция добавления ивентов"""

        # await message.delete()
        answer1 = await message.ask(
            f"**Введите дату дискотеки в формате** `{Utils.DATE_FORMAT}`"
        )
        date = datetime.datetime.strptime(answer1.content, Utils.DATE_FORMAT)
        answer2 = await message.ask(
            "**Введите числом максимальное количество пользователей или напишите**"
            "`выход` **для окончания создания события(стандратное число 250)**"
        )
        max_visitors = (
            int(answer2.content) if answer2.content.lower() != "выход" else 250
        )
        self.db.add_event(date, max_visitors)
        self.logger.warning(
            f"Пользователь {message.from_user.full_name}({message.from_user.id}) "
            f"добавил ивент на {date}"
        )

    async def handle_delevent_admin(self, message: Message):
        """Функция удаления ивентов"""

        # await message.delete()
        text = ""
        answer1 = await message.ask(
            "**Введите дату дискотеки которую хотите удалить в формате**"
            f"`{Utils.DATE_FORMAT}` или напишите `выход` для отмены"
        )
        if answer1.content.lower() != "выход":
            date = datetime.datetime.strptime(answer1.content, Utils.DATE_FORMAT)
            self.db.delete_event(date)
            text = f"**Событие** __{date}__ **успешно удалено!**"
            self.logger.warning(
                f"Пользователь {message.from_user.full_name}"
                f"({message.from_user.id}) удалил ивент на {date}"
            )
        else:
            text = "**Удаление события отменено!**"
            self.logger.info(
                "Пользователь %s (%s) отменил удаление ивента",
                message.from_user.full_name,
                message.from_user.id,
            )
        await answer1.reply(text)

    async def error_handler(self, error: Exception, context: str = ""):
        """Асинхронный обработчик ошибок"""
        error_msg = f"⚠️ **Ошибка в боте** ⚠️\n\n"
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

        try:
            for admin in Utils.ADMIN_IDS:
                await self.send_message(admin, error_msg)
        except Exception as e:
            self.logger.error(f"Ошибка при отправке сообщения: {e}")

    async def callbacks(self, _: Client, query: CallbackQuery):
        """Функция приёма колбеков"""
        data = str(query.data)
        message = query.message

        if data.startswith("useragreement"):
            await message.edit_text(
                """Пользовательское соглашение\n1. Общие положения\n1.1. Настоящее Пользовательское\nсоглашение (далее — «Соглашение») регулирует правила посещения дискотеки на базе Дома молодёжи (г. Боровичи, ул. 9 Января, д. 46) (далее —\n«Мероприятие»).\n1.2. Организатор оставляет за собой право вносить изменения в правила посещения и условия Соглашения.\nАктуальная версия всегда доступна на официальных ресурсах.\n1.3. Посещение Мероприятия означает согласие с условиями данного Соглашения.\n\n2. Условия посещения\n2.1. Мероприятие рекомендовано для лиц в возрасте от 14 до\n25 лет.\n2.2. Организатор в праве запросить предъявление документа, удостоверяющего возраст (паспорт, ученический билет с фото, справку из\nшколы).\n2.3. Вход строго запрещён лицам в состоянии алкогольного или наркотического опьянения\n\n3. Правила поведения\n3.1. Посетители обязаны:\n- Соблюдать общественный порядок и нормы морали.\n- Уважительно относиться к другим гостям и персоналу.\n- Выполнять требования администрации и охраны.\n3.2. Запрещено:\n- Употребление алкоголя, табака, наркотических веществ.\n- Ношение оружия, колюще-режущих предметов, взрывчатых\nвеществ.\n- Проявление агрессии, буллинга, дискриминации.\n- Порча имущества учреждения.\n3.3. В случае нарушений администрация вправе удалить посетителя без компенсации стоимости билета.\n\n4. Безопасность и контроль\n4.1. Организаторы проводят досмотр на входе для предотвращения проноса запрещённых предметов.\n4.2. В случае ЧП необходимо следовать указаниям\nперсонала.\n\n5. Ответственность\n5.1. Организатор не несёт ответственности за:\n- Личные вещи посетителей (рекомендуется не оставлять ценные вещи без присмотра).\n- Поведение посетителей вне территории Мероприятия.\n5.2. Родители/законные представители несовершеннолетних\nнесут ответственность за действия своих детей в рамках действующего законодательства.\n\n6. Прочие условия\n6.1. Организатор вправе использовать материалы с Мероприятия\nв рекламных целях.\n\n7. Условия использования кошелька\n7.1 Сумма, внесённая на счёт кошелька без весомой на то причины, не возвращается\n7.2 Возврат средств осуществляется на баланс кошелька исключительно при\nвозврате билета\n\nДата вступления в силу: 29.03.2025\nКонтакты организаторов:\nНиколаев Даниил Александрович\nstutututuf@gmail.com\nАжимиров Руслан Рамильевич\nazimirovr@mail.ru\nИванов Антон Андреевич\nmiiqwf@gmail.com""",
                reply_markup=ButtonsMenu.get_menu_markup(),
            )
            return
        if data.startswith("reg_error"):
            await query.answer("❌ Это событие закончилось или места кончились")
        if data.startswith("buytickets"):
            await message.edit_reply_markup(
                ButtonsMenu.get_buy_markup(query.from_user.id)
            )
        if data.startswith("menu"):
            await message.edit_text(Utils.START_MESSAGE)
            await message.edit_reply_markup(ButtonsMenu.get_start_markup())

        if data.startswith("reg_user_to"):
            date = datetime.datetime.strptime(
                "".join(data.split("_")[3:]), Utils.DATE_FORMAT
            )

            result = self.db.check_registration_by_tgid(query.from_user.id, date.date())
            if result:
                await query.answer("❌ Вы уже зарегистрированы на это событие!!!")
                return
            if self.db.is_event_is_full(date):
                await query.answer("❌ Это событие закончилось или места кончились")
                return
            cost = Utils.COST
            description = "Оплата прохода в клуб"
            # receipt: dict[str, str] = {
            #     "Email": "stutututuf@gmail.com",
            #     "Phone": "+79602051271",
            #     "Amount": str(cost * 100),
            #     "Description": description,
            # }
            # token = sha256("".join(receipt).encode()).hexdigest()
            # receipt["Token"] = token
            r = await self.tb.init_payment(
                cost,
                hash(query.from_user.id + time.time()),
                description,
                # receipt=receipt,
            )

            await message.edit_text(
                "Виды оплаты",
                reply_markup=ButtonsMenu.get_payment_button(r["PaymentURL"], cost),
            )
            if await self.tb.await_payment(r["PaymentId"]):

                self.logger.info(
                    f"Пользователь {query.from_user.full_name}({query.from_user.id})"
                    f" оплатил заказ {r['PaymentId']}"
                )
                try:
                    hash_code = self.db.reg_new_visitor(
                        query.from_user.id,
                        date,
                    )
                except AttributeError:
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
                    f"{''.join(data.split('_')[3:])}!\n\n\n__Резервный код__:\n`{hash_code}`",
                )
                self.logger.info(
                    "Пользователь %s (%s) получил код %s",
                    query.from_user.full_name,
                    query.from_user.id,
                    hash_code,
                )

            else:
                try:
                    await message.edit_text(
                        "Оплата отклонена, попробуйте позже"
                    )
                except MessageNotModified:
                    pass
