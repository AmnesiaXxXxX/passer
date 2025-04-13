from datetime import datetime
from enum import Enum

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from classes.database import Database
from utils import Utils


class Buttons_Menu(Enum):
    @staticmethod
    def decline_tickets(number: int) -> str:
        """
        Склоняет слово "билет" в зависимости от числа.
        Примеры:
            1 билет
            2 билета
            5 билетов
            21 билет
            22 билета
            25 билетов
        """
        if number % 10 == 1 and number % 100 != 11:
            return "билет"
        elif 2 <= number % 10 <= 4 and (number % 100 < 10 or number % 100 >= 20):
            return "билета"
        else:
            return "билетов"

    @classmethod
    def get_buy_markup(cls, tg_id: int | str):
        db = Database()
        user = db.check_registration_by_tgid
        buttons = []

        for date in db.get_events(display_all=True, show_old=False):
            available = db.get_available_slots(date[0])
            button_text = f"{datetime.strptime(date[0], Utils.DATE_FORMAT).strftime('%d.%m.%Y')} ({available} {Buttons_Menu.decline_tickets(available)}) {'✅' if user(tg_id, date[0]) else ''}

            button = InlineKeyboardButton(
                button_text,
                f"reg_user_to_{date[0]}" if date[2] - date[1] > 0 else "reg_error",
            )
            buttons.append(button)

        buttons.append(Buttons_Menu.get_menu())

        # Разбиваем кнопки на группы по 3
        return InlineKeyboardMarkup(
            [buttons[i : i + 1] for i in range(0, len(buttons))]
        )

    @classmethod
    def get_start_markup(cls) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Купить билеты", "buytickets")],
                [
                    InlineKeyboardButton(
                        "📝Пользовательское соглашение", "useragreement"
                    ),
                ],
            ]
        )

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
        return InlineKeyboardButton("🗄 В меню", callback_data="menu")

    @staticmethod
    def get_menu_markup():
        return InlineKeyboardMarkup([[Buttons_Menu.get_menu()]])
