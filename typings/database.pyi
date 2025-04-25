from _typeshed import Incomplete
from datetime import date, datetime
from sqlalchemy import Column
from sqlalchemy.orm import Session as Session
from typing import overload

Base: Incomplete

class Visitor(Base):
    __tablename__: str
    id: str | int
    tg_id: str | int
    to_datetime: datetime | date
    hash_code: str
    is_active: bool | Column[bool]

class User(Base):
    __tablename__: str
    id: str | int
    tg_id: str | int

class Registration(Base):
    __tablename__: str
    id: str | int
    date: date
    max_visitors: int | Column[int]
    visitors_count: int | Column[int]

class Database:
    db_name: str
    engine: Incomplete
    Session: Incomplete
    logger: Incomplete
    backup_dir: str
    dump_interval: int | float
    def __init__(self, name: str = "database") -> None: ...
    def get_session(self) -> Session: ...
    def get_all_visitors(self, q: str | int | None = None) -> list[Visitor]: ...
    def get_user_hashcode(
        self, tg_id: str | int, to_datetime: date | datetime
    ) -> str: ...
    def get_all_users(self) -> list[User]: ...
    def add_user(self, tg_id: str | int) -> bool: ...
    @overload
    def enable_visitor(
        self,
        *,
        tg_id: int | str | None = None,
        to_datetime: datetime | date | None = None
    ) -> str: ...
    @overload
    def enable_visitor(self, *, hash_code: str | None = None) -> str: ...
    def reg_new_visitor(
        self, tg_id: str | int, to_datetime: datetime, is_active: bool = True
    ) -> str: ...
    def delete_visitor(
        self, tg_id: str | int, to_datetime: date | None = None
    ) -> None: ...
    def disable_visitor(self, hash_code: str) -> bool: ...
    def check_registration_by_hash(
        self, hash_code: str, is_strict: bool = True
    ) -> Visitor | None: ...
    def check_registration_by_tgid(
        self, tg_id: str | int, to_datetime: date, is_active: bool = True
    ) -> bool: ...
    def get_available(self, date: str | date | Column[date]) -> int: ...
    def get_events(
        self, show_all: bool = False, show_old: bool = True
    ) -> list[Registration]: ...
    def is_event_full(self, to_datetime: date) -> bool: ...
    def add_event(self, to_datetime: date, max_visitors: int) -> None: ...
    def delete_event(self, to_datetime: date) -> None: ...
