"""Модуль кастомного класса клиента тинькоффа"""

import asyncio
import time

from tinkoff_acquiring.client import TinkoffAcquiringAPIClient, TinkoffAPIException


class CustomTinkoffAcquiringAPIClient(TinkoffAcquiringAPIClient):
    """Класс кастомного класса клиента тинькоффа"""

    def __init__(self, terminal_key: str | None, secret: str | None):
        if not (terminal_key, secret):
            raise ValueError("terminal_key и secret не могут быть пустыми")
        super().__init__(terminal_key, secret)

    async def await_payment(self, order_id: str, timeout: float = 240.0) -> bool:
        """
        Ждем подтверждения оплаты в течение заданного времени (timeout, по умолчанию 60 секунд).
        Возвращает True если оплата подтверждена, иначе False.
        Завершает цикл, если бот выключается.
        """
        state = ""
        start = time.monotonic()

        while time.monotonic() - start < timeout:
            try:
                result = await self.get_payment_state(order_id)
                state = result["Status"]
                if state:
                    if state == "CONFIRMED":
                        return True
                    if state == "FORM_SHOWED":
                        timeout *= 2
            except TinkoffAPIException:
                pass
            except asyncio.CancelledError:
                break

            await asyncio.sleep(10)
        return False
