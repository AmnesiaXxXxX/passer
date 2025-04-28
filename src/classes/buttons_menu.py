"""Модуль кнопок меню с использованием SQLAlchemy"""

from datetime import datetime
from typing import Union, List

from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButtonBuy,
)

from src.classes.database import Database
from src.utils import Utils


class ButtonsMenu:
    """Класс для генерации интерактивных кнопок меню"""

    @staticmethod
    def _decline_tickets(number: int) -> str:
        """Склоняет слово 'билет' в зависимости от числа"""
        if number % 10 == 1 and number % 100 != 11:
            return "билет"
        if 2 <= number % 10 <= 4 and (number % 100 < 10 or number % 100 >= 20):
            return "билета"
        return "билетов"

    @classmethod
    def get_buy_markup(cls, tg_id: Union[int, str]) -> InlineKeyboardMarkup:
        """Генерирует клавиатуру для покупки билетов"""
        with Database().get_session():
            db = Database()
            buttons: List[InlineKeyboardButton] = []

            # Получаем доступные события
            events = db.get_events(show_all=True, show_old=False)

            for event in events:
                # Ensure we're working with actual integer values
                available = db.get_available(event.date)
                date_obj = datetime.strptime(str(event.date), Utils.DATE_FORMAT)

                # Проверяем регистрацию пользователя
                is_registered = db.check_registration_by_tgid(tg_id, date_obj.date())

                # Формируем текст кнопки
                button_text = (
                    f"{date_obj.strftime('%d.%m.%Y')} "
                    f"({available} {cls._decline_tickets(available)})"
                    f"{' ✅' if is_registered else ''}"
                )

                # Определяем callback данные
                if is_registered:
                    callback_data = "reg_error_already_registrate"
                elif available <= 0:
                    callback_data = "reg_error_not_available"
                else:
                    callback_data = f"reg_user_to_{event.date}"

                buttons.append(
                    InlineKeyboardButton(button_text, callback_data=callback_data)
                )

            # Добавляем кнопку меню
            buttons.append(cls._get_menu_button())

            # Группируем кнопки по 1 в ряд
            keyboard: List[List[InlineKeyboardButton | InlineKeyboardButtonBuy]] = [
                [button] for button in buttons
            ]

            return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_newsletter_markup(tg_id: Union[int, str]) -> InlineKeyboardMarkup:
        """Генерирует клавиатуру для подтверждения рассылки"""
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Отправить", callback_data=f"send_{tg_id}"),
                    InlineKeyboardButton("Отмена", callback_data="send_cancel"),
                ]
            ]
        )

    @staticmethod
    def get_start_markup() -> InlineKeyboardMarkup:
        """Генерирует стартовую клавиатуру"""
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Купить билеты", callback_data="buytickets")],
                [
                    InlineKeyboardButton(
                        "📝 Пользовательское соглашение", callback_data="useragreement"
                    )
                ],
            ]
        )

    @classmethod
    def get_payment_markup(cls, payment_url: str, cost: int) -> InlineKeyboardMarkup:
        """Генерирует клавиатуру для оплаты"""
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(f"Оплатить {cost} ₽", url=payment_url)],
            ]
        )

    @staticmethod
    def _get_menu_button() -> InlineKeyboardButton:
        """Возвращает кнопку возврата в меню"""
        return InlineKeyboardButton("🗄 В меню", callback_data="menu")

    @staticmethod
    def get_menu_markup() -> InlineKeyboardMarkup:
        """Генерирует минимальную клавиатуру с кнопкой меню"""
        return InlineKeyboardMarkup([[ButtonsMenu._get_menu_button()]])
