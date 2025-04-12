from enum import Enum
from typing import Dict, Optional

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from classes.database import Database


class Buttons_Menu(Enum):
    DB = Database()
    __enum__: Dict[str | int, InlineKeyboardMarkup] = {
        0: InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"Купить билет на {date[0]}", f"reg_user_to_{date[0]}"
                    )
                    for date in DB.get_events()
                ],
            ]
        ),
    }

    @classmethod
    def get(cls, key: int) -> Optional[InlineKeyboardMarkup]:
        return cls.__enum__.get(key)

    @classmethod
    def get_payment_button(cls, payment_url: str, cost: int):
        return (
            InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            f"Оплатить с помощью Т-Банк ({cost} р.)", url=payment_url
                        )
                    ],
                ]
            )
        )
