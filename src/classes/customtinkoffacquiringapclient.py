import asyncio
import time

from tinkoff_acquiring.client import TinkoffAcquiringAPIClient, TinkoffAPIException


class CustomTinkoffAcquiringAPIClient(TinkoffAcquiringAPIClient):
    def __init__(self, terminal_key: str | None, secret: str | None):
        if not (terminal_key, secret):
            raise ValueError("terminal_key и secret не могут быть пустыми")
        super().__init__(terminal_key, secret)

    async def await_payment(self, order_id: str, timeout: float = 60.0) -> bool:
        """
        Ждем подтверждения оплаты в течение заданного времени (timeout, по умолчанию 60 секунд).
        Возвращает True если оплата подтверждена, иначе False.
        Завершает цикл, если бот выключается.
        """
        state = ""
        start = time.monotonic()
        print(f"Выход: {hash(order_id)}")

        while time.monotonic() - start < timeout:
            try:
                result = await self.get_payment_state(order_id)
                state = result["Status"]
                if state:
                    if state == "CONFIRMED":
                        return True
                    if state == "REJECTED":
                        return False
                    if state == "FORM_SHOWED":
                        timeout = 240
            except TinkoffAPIException:
                pass
            except asyncio.CancelledError:
                break

            await asyncio.sleep(2)
        return False
