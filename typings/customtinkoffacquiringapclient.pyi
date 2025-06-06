from tinkoff_acquiring.client import TinkoffAcquiringAPIClient

class CustomTinkoffAcquiringAPIClient(TinkoffAcquiringAPIClient):
    terminal_key: str | None
    def __init__(self, terminal_key: str | None, secret: str | None) -> None: ...
    async def await_payment(self, order_id: str, timeout: float = 240.0) -> bool: ...
