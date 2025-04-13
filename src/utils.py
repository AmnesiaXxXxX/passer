"""Утилиты для бота"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

import PIL
import PIL.Image
import qrcode


def get_env_admin_ids() -> list[int | str]:
    # Получаем значение из переменной окружения или используем значение по умолчанию
    ids_str = os.getenv("ADMIN_IDS", "5957115070,831985431")
    return [
        int(x.strip()) if x.strip().isdigit() else x.strip() for x in ids_str.split(",")
    ]


class Utils:
    """Класс утилит"""

    START_MESSAGE: str = (
        """Привет!\nЭтот бот нужен для оплаты пропуска на вечеринку \n"""
    )
    DATE_FORMAT: str = "%d/%m/%Y, %H:%M:%S"
    ADMIN_IDS: list[int | str] = get_env_admin_ids()

    @classmethod
    def updateAdminIDs(cls) -> None:
        # Обновляет список ADMIN_IDS из .env файла
        cls.ADMIN_IDS = get_env_admin_ids()

    @staticmethod
    async def genQRCode(data: str | list[str]):
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
