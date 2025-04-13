from enum import Enum
from typing import Dict, Optional

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from classes.database import Database


class Buttons_Menu(Enum):

    @classmethod
    def get(cls, tg_id: int) -> Optional[InlineKeyboardMarkup]:
        db = Database()
        user = db.check_registration_by_tgid

        # Создаем список всех кнопок
        buttons = [
            InlineKeyboardButton(
                f"{date[0]} {'✅' if user(tg_id, date[0]) else '❌'}",
                f"reg_user_to_{date[0]}",
            )
            for date in db.get_events()
        ]

        # Разбиваем кнопки на группы по 3
        button_rows = [buttons[:3]]

        # Добавляем кнопку соглашения в последний ряд
        button_rows.append(
            [
                InlineKeyboardButton("📝Пользовательское соглашение", "useragreement"),
            ],
        )

        return InlineKeyboardMarkup(button_rows)

    @classmethod
    def get_payment_button(cls, payment_url: str, cost: int):
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"Оплатить с помощью Т-Банк ({cost} р.)", url=payment_url
                    )
                ],
                [Buttons_Menu.get_menu()],
            ]
        )

    @staticmethod
    def get_menu():
        return InlineKeyboardButton("🗄 В меню", callback_data="open_menu")

    @staticmethod
    def get_menu_markup():
        return InlineKeyboardMarkup([[Buttons_Menu.get_menu()]])
