from pyrogram.client import Client
from pyrogram.types import (
    CallbackQuery as CallbackQuery,
    Message as Message,
    User as User,
)
from typing import TypeVar
from logging import Logger
from .database import Database
from .customtinkoffacquiringapclient import CustomTinkoffAcquiringAPIClient

ClientVar = TypeVar("ClientVar")

class CustomClient(Client):
    logger: Logger
    db: Database
    tb: CustomTinkoffAcquiringAPIClient
    messages: dict[str, str]
    def __init__(
        self,
        name: str = "bot",
        api_id: str | int | None = None,
        api_hash: str | None = None,
        bot_token: str | None = None,
    ) -> None: ...
    async def handle_genqr_admin(self, _, message: Message) -> None: ...
    async def handle_check_admin(self, message: Message) -> None: ...
    async def handle_sendall_admin(self, message: Message) -> None: ...
    async def handle_getmyqr(self, _, message: Message) -> None: ...
    async def handle_main_start(self, _: Client, message: Message) -> None: ...
    async def handle_addevent_admin(self, _, message: Message) -> None: ...
