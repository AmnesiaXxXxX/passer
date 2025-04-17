"""Модуль кнопок меню"""

from typing import List, Union
from datetime import datetime

from pyrogram.client import Client
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButtonBuy,
    Message,
)

from src.classes.database import Database
from src.utils import Utils


class ButtonsMenu:
    """Класс кнопок"""

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
        if 2 <= number % 10 <= 4 and (number % 100 < 10 or number % 100 >= 20):
            return "билета"
        return "билетов"

    @classmethod
    def get_buy_markup(cls, tg_id: int | str):
        """Возвращает маркап кнопок для покупки"""
        db = Database()
        check = db.check_registration_by_tgid
        buttons: List[Union[InlineKeyboardButton, InlineKeyboardButtonBuy]] = []

        for date in db.get_events(display_all=True, show_old=False):
            available = db.get_available_slots(date[0])
            button_text = (
                f"{datetime.strptime(date[0], Utils.DATE_FORMAT).strftime('%d.%m.%Y')}"
                f"({available} {ButtonsMenu.decline_tickets(available)})"
                f"{'✅' if check(tg_id, date[0], is_active=None) else ''}"
            )
            callback_text = (
                f"reg_user_to_{date[0]}" if date[2] - date[1] > 0 else "reg_error"
            )
            if check(tg_id, date[0], True):
                callback_text = "reg_error_already_registrate"
            button = InlineKeyboardButton(
                button_text,
                callback_text,
            )
            buttons.append(button)

        buttons.append(ButtonsMenu.get_menu())
        result = [buttons[i : i + 1] for i in range(0, len(buttons))]
        # Разбиваем кнопки на группы по 3
        return InlineKeyboardMarkup(result)

    @staticmethod
    def get_newsletter_markup(tg_id: int | str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Отправить", f"send_{tg_id}"),
                    InlineKeyboardButton("Отмена", f"send_cancel"),
                ],
            ]
        )

    @staticmethod
    def get_start_markup() -> InlineKeyboardMarkup:
        """Возвращает стартовый маркап с кнопками"""
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
        """Возвращает кнопку оплаты через Т-Банк"""
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"Оплатить с помощью Т-Банк ({cost} р.)", url=payment_url
                    )
                ],
                [ButtonsMenu.get_menu()],
            ]
        )

    @staticmethod
    def get_menu():
        """Возвращает кнопку меню"""
        return InlineKeyboardButton("🗄 В меню", callback_data="menu")

    @staticmethod
    def get_menu_markup():
        """Возвращает маркап кнопок меню"""
        return InlineKeyboardMarkup([[ButtonsMenu.get_menu()]])
