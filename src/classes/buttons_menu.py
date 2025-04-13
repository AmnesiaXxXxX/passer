from enum import Enum
from typing import Dict, Optional

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from classes.database import Database


class Buttons_Menu(Enum):

    @classmethod
    def get(cls, tg_id: int) -> Optional[InlineKeyboardMarkup]:
        db = Database()
        user = db.get_all_visitors(tg_id)[0]
        buttons = [
            InlineKeyboardButton(
                f"'{date[0]}' {'✅' if user[3] else '❌'}",
                f"reg_user_to_{date[0]}",
            )
            for date in db.get_events()
        ]
        buttons.append(
            InlineKeyboardButton("📝Пользовательское соглашение", "useragreement")
        )
        return InlineKeyboardMarkup([buttons])

    @classmethod
    def get_payment_button(cls, payment_url: str, cost: int):
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"Оплатить с помощью Т-Банк ({cost} р.)", url=payment_url
                    )
                ],
            ]
        )
