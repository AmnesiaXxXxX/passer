"""Модуль базы данных"""

import hashlib
import sqlite3 as sql
from datetime import UTC, datetime
from typing import List, Optional

from utils import Utils


class Database:
    def __init__(self, name: str = "database"):
        self.con = sql.connect(name + ".db", check_same_thread=False, autocommit=True)
        self.cur = self.con.cursor()
        self.create_tables()  # Добавлено: создание таблиц при старте

    def create_tables(self):
        # Создание таблицы visitors, если не существует
        self.cur.execute(
            """
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id TEXT NOT NULL,
            to_datetime TEXT NOT NULL,
            hash_code TEXT NOT NULL
        )
        """
        )
        # Создание таблицы registrations, если не существует
        self.cur.execute(
            """
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id TEXT,
            event_date TEXT
        )
        """
        )

    def get_all_visitors(self, q: Optional[str | int] = None) -> List[str]:
        query = "SELECT * FROM visitors"
        if q:
            query += (
                f"\nWHERE tg_id LIKE '%' || '{q}' || '%' OR"
                f"\nto_datetime LIKE '%' || '{q}' || '%' OR"
                f"\nhash_code LIKE '%' || '{q}' || '%'"
            )
        self.cur.execute(query)
        return self.cur.fetchall()

    @staticmethod
    def generate_hash(tg_id: int | str, dt: datetime) -> str:
        data = f"{tg_id}{dt.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()

    def reg_new_visitor(
        self,
        tg_id: int | str,
        to_datetime: datetime,
        *,
        entry_datetime: Optional[datetime] = None,
    ):
        for event in self.get_all_visitors(tg_id):
            print(
                (
                    datetime.strptime(event[1], "%Y-%d-%m %H:%M:%S"),
                    to_datetime.strftime(Utils.DATE_FORMAT),
                )
            )

            if datetime.strptime(
                event[1], "%Y-%d-%m %H:%M:%S"
            ) == to_datetime.strftime(Utils.DATE_FORMAT):
                raise AttributeError(
                    "Такой пользователь уже зарегистрирован на это событие!"
                )
        if entry_datetime is None:
            entry_datetime = datetime.now(UTC)
        hash_code = self.generate_hash(tg_id, entry_datetime)
        query = "INSERT INTO visitors (tg_id, to_datetime, hash_code) VALUES (?, ?, ?)"
        self.cur.execute(query, (str(tg_id), to_datetime, hash_code))
        return hash_code

    def delete_visitor(
        self, tg_id: int | str, to_datetime: Optional[datetime] = None
    ) -> None:
        """
        Удаляет пользователя из базы данных.
        Если задан to_datetime, удаляет запись с указанными tg_id и to_datetime.
        Иначе удаляются все записи с указанным tg_id.
        """
        if to_datetime is None:
            query = "DELETE FROM visitors WHERE tg_id=?"
            self.cur.execute(query, (str(tg_id),))
        else:
            query = "DELETE FROM visitors WHERE tg_id=? AND to_datetime=?"
            self.cur.execute(query, (str(tg_id), to_datetime))

    def get_events(self):
        query = "SELECT * FROM registrations"
        self.cur.execute(query)

        return self.cur.fetchall()
