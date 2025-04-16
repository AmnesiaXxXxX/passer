"""Утилиты для бота"""

import asyncio
import os
from datetime import datetime
from typing import Any, Callable, TypeVar, cast

import PIL
import PIL.Image
import qrcode
from dotenv import load_dotenv
from pyrogram.types import Message
import hashlib

load_dotenv()
T = TypeVar("T")


def get_env_admin_ids() -> list[int | str]:
    """Получаем значение из переменной окружения или используем значение по умолчанию"""
    ids_str = os.getenv("ADMIN_IDS", "5957115070,831985431")
    return [
        int(x.strip()) if x.strip().isdigit() else x.strip() for x in ids_str.split(",")
    ]


class Utils:
    """Класс утилит"""

    START_MESSAGE: str = """**🔥 Добро пожаловать в бот дискотеки S.T.A.R! 🔥**"""
    DATE_FORMAT: str = "%Y-%m-%d"
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    ADMIN_IDS: list[int | str] = get_env_admin_ids()
    TRUE_CODE = "`✅ Код верный!`"
    FALSE_CODE = "`❌ Код неверный!`"
    FALSE_CODE_ALREADY_USED = "`❌ Код уже был использован!`"
    COST = 250

    @staticmethod
    def generate_hash(tg_id: int | str, dt: datetime) -> str:
        """Внутренняя функция генерация хеша"""
        data = f"{tg_id}{dt.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()

    @classmethod
    def update_admin_ids(cls) -> None:
        """Обновляет список ADMIN_IDS из .env файла"""
        cls.ADMIN_IDS = get_env_admin_ids()

    @staticmethod
    def event_exception_handler(func: Callable[..., T]) -> Callable[..., T]:
        """Декоратор для обработки исключений при работе с событиями"""

        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            except ValueError:
                message = next((arg for arg in args if isinstance(arg, Message)), None)
                if message:
                    date = datetime.now().strftime(Utils.DATE_FORMAT)
                    await message.reply(f"**Ошибка формата!** \nПример: `{date}`")
                raise
            except Exception as e:
                message = next((arg for arg in args if isinstance(arg, Message)), None)
                if message:
                    await message.reply(f"⚠️ Произошла ошибка: {str(e)}")
                raise

        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            return cast(T, async_wrapper(*args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    @staticmethod
    async def gen_qr_code(data: str | list[str]):
        """Асинхронная генерация QR-кода.

        Args:
            data (str | list[str]): Данные для генерации QR-кода. Если передается список,
                                      его элементы будут объединены в одну строку.

        Returns:
            PIL.Image.Image: Сгенерированное изображение QR-кода.
        """

        def create_qr() -> PIL.Image.Image:
            qr = qrcode.QRCode(
                version=2,
                error_correction=qrcode.ERROR_CORRECT_H,
                box_size=10,
                border=3,
            )
            if isinstance(data, list):
                data_str = " ".join(data)
            else:
                data_str = data
            qr.add_data(data_str)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            return img.get_image()

        return await asyncio.to_thread(create_qr)


#
