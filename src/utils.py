"""Утилиты для бота"""

import asyncio
import hashlib
import os
from datetime import datetime
from typing import Any, Callable, TypeVar, Union, cast

import PIL
import PIL.ImageOps
import qrcode
from dotenv import load_dotenv
from PIL import Image
from pyrogram.types import Message
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import ImageColorMask
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer

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
    TRUE_PROMPT = "Ваш QR-код на {0}:\n`{1}`"
    SUCCESS_URL = "https://t.me/{0}?start=activate{1}".format
    TRUE_CODE = "`✅ Код верный!`"
    FALSE_CODE = "`❌ Код неверный!`"
    FALSE_CODE_ALREADY_USED = "`❌ Код уже был использован!`"
    CALLBACK_USER_ALREADY_REGISTRATE = "❌ Вы уже были зарегистрированы!"
    CALLBACK_USER_NOT_AVAILABLE = "❌ Места на это событие кончились!"
    QR_URL = "https://t.me/{0}?start={1}".format
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
    def create_qr(data: Union[str, list[str]]) -> Image.Image:
        """Генерация QR-кода с использованием изображения в качестве цветовой маски.

        Args:
            data (str | list[str]): Данные для генерации QR-кода. Если передается список,
                                    его элементы будут объединены в одну строку.

        Returns:
            PIL.Image.Image: Сгенерированное изображение QR-кода с цветовой маской.
        """
        # Создаем объект QR-кода
        qr = qrcode.QRCode(
            version=2,
            error_correction=qrcode.ERROR_CORRECT_H,
            box_size=10,
            border=3,
        )

        # Обрабатываем входные данные
        if isinstance(data, list):
            data_str = " ".join(data)
        else:
            data_str = data

        # Добавляем данные в QR-код
        qr.add_data(data_str)
        qr.make(fit=True)

        # Создаем изображение с кастомной цветовой маской
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=RoundedModuleDrawer(),
            color_mask=ImageColorMask((89, 88, 86), color_mask_path="image.png"),
        )

        return img.get_image()

    @classmethod
    async def gen_qr_code(cls, data: str | list[str]):
        """Асинхронная генерация QR-кода.

        Args:
            data (str | list[str]): Данные для генерации QR-кода. Если передается список,
                                      его элементы будут объединены в одну строку.

        Returns:
            PIL.Image.Image: Сгенерированное изображение QR-кода.
        """

        return await asyncio.to_thread(cls.create_qr, data)


#
