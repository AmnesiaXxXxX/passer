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

    async def handle_check_admin(self, message: Message):
        if self.db.check_registration_by_hash(message.command[1], is_active=True):
            await message.reply(Utils.TRUE_CODE)
            self.db.disable_visitor(message.command[1])
        elif self.db.check_registration_by_hash(message.command[1]):
            await message.reply(Utils.FALSE_CODE_ALREADY_USED)
        else:
            await message.reply(Utils.FALSE_CODE)

    async def handle_main_start_help(self, message: Message):
        """Главная функция для команд `main|start|help`"""
        print(message.from_user.id)
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
            Utils.START_MESSAGE, reply_markup=Buttons_Menu.get(message.from_user.id)
        )

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
        message = query.message

        if data.startswith("useragreement"):
            msg = await client.send_message(
                query.from_user.id,
                """Пользовательское соглашение\n1. Общие положения\n1.1. Настоящее Пользовательское\nсоглашение (далее — «Соглашение») регулирует правила посещения дискотеки на базе Дома молодёжи (г. Боровичи, ул. 9 Января, д. 46) (далее —\n«Мероприятие»).\n1.2. Организатор оставляет за собой право вносить изменения в правила посещения и условия Соглашения.\nАктуальная версия всегда доступна на официальных ресурсах.\n1.3. Посещение Мероприятия означает согласие с условиями данного Соглашения.\n\n2. Условия посещения\n2.1. Мероприятие рекомендовано для лиц в возрасте от 14 до\n25 лет.\n2.2. Организатор в праве запросить предъявление документа, удостоверяющего возраст (паспорт, ученический билет с фото, справку из\nшколы).\n2.3. Вход строго запрещён лицам в состоянии алкогольного или наркотического опьянения\n\n3. Правила поведения\n3.1. Посетители обязаны:\n- Соблюдать общественный порядок и нормы морали.\n- Уважительно относиться к другим гостям и персоналу.\n- Выполнять требования администрации и охраны.\n3.2. Запрещено:\n- Употребление алкоголя, табака, наркотических веществ.\n- Ношение оружия, колюще-режущих предметов, взрывчатых\nвеществ.\n- Проявление агрессии, буллинга, дискриминации.\n- Порча имущества учреждения.\n3.3. В случае нарушений администрация вправе удалить посетителя без компенсации стоимости билета.\n\n4. Безопасность и контроль\n4.1. Организаторы проводят досмотр на входе для предотвращения проноса запрещённых предметов.\n4.2. В случае ЧП необходимо следовать указаниям\nперсонала.\n\n5. Ответственность\n5.1. Организатор не несёт ответственности за:\n- Личные вещи посетителей (рекомендуется не оставлять ценные вещи без присмотра).\n- Поведение посетителей вне территории Мероприятия.\n5.2. Родители/законные представители несовершеннолетних\nнесут ответственность за действия своих детей в рамках действующего законодательства.\n\n6. Прочие условия\n6.1. Организатор вправе использовать материалы с Мероприятия\nв рекламных целях.\n\n7. Условия использования кошелька\n7.1 Сумма, внесённая на счёт кошелька без весомой на то причины, не возвращается\n7.2 Возврат средств осуществляется на баланс кошелька исключительно при\nвозврате билета\n\nДата вступления в силу: 29.03.2025\nКонтакты организаторов:\nНиколаев Даниил Александрович\nstutututuf@gmail.com\nАжимиров Руслан Рамильевич\nazimirovr@mail.ru\nИванов Антон Андреевич\nmiiqwf@gmail.com""",
                reply_markup=Buttons_Menu.get_menu_markup(),
            )
            return
        if data.startswith("menu"):
            await self.handle_main_start_help(message)
        if data.startswith("reg_user_to"):
            date = datetime.datetime.strptime(
                "".join(data.split("_")[3:]), Utils.DATE_FORMAT
            )

            result = self.db.check_registration_by_tgid(query.from_user.id, date.date())
            print(f"Результат: {result}")
            if result:
                await query.answer("❌ Вы уже зарегистрированы на это событие!!!")
                return
            if self.db.is_event_is_full(date):
                await query.answer("❌ Это событие закончилось или места кончились")
                return
            cost = Utils.COST
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
                try:
                    hash_code = self.db.reg_new_visitor(
                        query.from_user.id,
                        date,
                    )
                except AttributeError:
                    msg = await client.send_message(
                        query.from_user.id,
                        "`❌ Вы уже зарегистрированы на это событие!!!`",
                    )
                    return
                msg = await client.send_message(
                    query.from_user.id, "Подождите, идёт генерация Вашего QR кода!"
                )
                image = await Utils.genQRCode(
                    f"https://t.me/{self.me.username}?start={hash_code}"
                )
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format="PNG")
                img_byte_arr.seek(0)
                await msg.reply_photo(
                    photo=img_byte_arr,
                    caption=f"Ваш QR на дискотеку {"".join(data.split("_")[3:])}!\n\n\n__Резервный код__:\n`{hash_code}`",
                )
                await client.delete_messages(chat_id=msg.chat.id, message_ids=msg.id)
            else:
                try:
                    await msg.edit_text("Оплата отклонена, попробуйте позже")
                except Exception:
                    pass
        await message.delete()

    def run(self, coroutine: Optional[Coroutine[Any, Any, Any]] = None) -> None:
        """Запуск клиента"""
        self.logger.info(f"Старт бота в {datetime.datetime.now(datetime.UTC)}")
        super().run(coroutine)
