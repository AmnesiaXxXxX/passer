"""Модуль базы данных"""

import hashlib
import sqlite3 as sql
from datetime import UTC, date, datetime
from typing import List, Optional


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

    def get_all_visitors(self, q: Optional[str | int | datetime] = None) -> List[str]:
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
            # Try parsing with date first, then datetime if that fails
            try:
                event_datetime = datetime.strptime(event[1], "%Y-%m-%d")  # Date only
            except ValueError:
                try:
                    event_datetime = datetime.strptime(event[1], "%Y-%m-%d %H:%M:%S")
                except ValueError as e:
                    raise ValueError(
                        f"Could not parse datetime string: {event[1]}"
                    ) from e

            if event_datetime.date() == to_datetime.date():
                raise AttributeError(
                    "Такой пользователь уже зарегистрирован на это событие!"
                )

        if entry_datetime is None:
            entry_datetime = datetime.now(UTC)
        hash_code = self.generate_hash(tg_id, entry_datetime)
        query = "INSERT INTO visitors (tg_id, to_datetime, hash_code) VALUES (?, ?, ?)"
        self.cur.execute(query, (str(tg_id), to_datetime.date(), hash_code))
        return hash_code

    def delete_visitor(
        self, tg_id: int | str, to_datetime: Optional[datetime | str] = None
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

    def disable_visitor(self, hash_code: str):
        """Деактивирует посетителя по хеш-коду (устанавливает is_active = 0)"""
        try:
            # Обновляем запись посетителя
            self.cur.execute(
                "UPDATE visitors SET is_active = 0 WHERE hash_code = ?", (hash_code,)
            )

            # Получаем дату посетителя для обновления счетчика
            self.cur.execute(
                "SELECT to_datetime FROM visitors WHERE hash_code = ?", (hash_code,)
            )
            visitor_date = self.cur.fetchone()

            if visitor_date:
                # Обновляем счетчик в таблице registrations
                self.cur.execute(
                    """UPDATE registrations
                    SET visitors_count = (
                        SELECT COUNT(*)
                        FROM visitors
                        WHERE to_datetime = ? AND is_active = 1
                    )
                    WHERE date = ?""",
                    (visitor_date[0], visitor_date[0]),
                )

            self.con.commit()
            return True
        except Exception as e:
            self.con.rollback()
            print(f"Ошибка при деактивации посетителя: {e}")
            return False

    def get_available_slots(self, date: str) -> int:
        """Возвращает количество оставшихся свободных мест для указанного события."""
        query = """
            SELECT (max_visitors - visitors_count) AS available_slots
            FROM registrations
            WHERE date = ?
        """
        self.cur.execute(query, (date,))
        result = self.cur.fetchone()
        return result[0] if result else 0

    def check_registration_by_hash(self, hash_code: str, is_active: bool = False):
        query = "SELECT * FROM visitors WHERE hash_code = ?"
        if is_active:
            query += " AND is_active == 1"
        self.cur.execute(query, (hash_code,))
        if self.cur.fetchone():
            return True
        else:
            return False

    def check_registration_by_tgid(self, tg_id: int | str, to_datetime: datetime | date):
        query = "SELECT * FROM visitors WHERE tg_id = ? AND to_datetime = ? AND is_active = 1"
        self.cur.execute(
            query,
            (
                tg_id,
                to_datetime,
            ),
        )

        return len(self.cur.fetchall()) > 0

    def get_events(self, display_all: bool = False, show_old: bool = True):
        query = "SELECT * FROM registrations"
        conditions = []

        if not display_all:
            conditions.append("visitors_count < max_visitors")
        if not show_old:
            conditions.append("date(date, '+1 day') > date('now', 'localtime')")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY date ASC"  # Добавляем сортировку по дате

        self.cur.execute(query)
        return self.cur.fetchall()

    def is_event_is_full(self, date: datetime):
        query = "SELECT * FROM registrations WHERE visitors_count < max_visitors AND date == ?"
        self.cur.execute(query, (str(date.date()),))
        result = self.cur.fetchone()
        print(date.date(), result)
        if result:
            return False
        return True

    def add_event(self, date: datetime, max_visitors: int) -> None:
        """Добавляет или обновляет событие в расписании."""
        query = """
            INSERT INTO registrations (date, max_visitors, visitors_count)
            VALUES (?, ?, 0)
            ON CONFLICT(date) DO UPDATE SET
                max_visitors = excluded.max_visitors
        """
        self.cur.execute(query, (date.date().isoformat(), max_visitors))
        self.con.commit()

    def delete_event(self, date: datetime) -> None:
        """Полностью удаляет событие и связанные регистрации."""
        date_str = date.date().isoformat()

        # Удаляем связанных посетителей
        self.cur.execute("DELETE FROM visitors WHERE to_datetime = ?", (date_str,))
        # Удаляем само событие
        self.cur.execute("DELETE FROM registrations WHERE date = ?", (date_str,))
        self.con.commit()
