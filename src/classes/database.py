"""Модуль базы данных с использованием SQLAlchemy"""

import glob
import logging
import os
import sqlite3
import threading
import time
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, overload

from sqlalchemy import Boolean, Column, Date, Integer, String, create_engine, func, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from src.utils import Utils

Base = declarative_base()


class Visitor(Base):
    __tablename__ = "visitors"
    id = Column(Integer, primary_key=True)
    tg_id = Column(String, nullable=False)
    to_datetime = Column(Date, nullable=False)
    hash_code = Column(String, nullable=False, unique=True)
    is_active: bool | Column[bool] = Column(Boolean, default=True)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(String, nullable=False, unique=True)


class Registration(Base):
    __tablename__ = "registrations"
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, unique=True)
    max_visitors: int | Column[int] = Column(Integer, nullable=False)
    visitors_count: int | Column[int] = Column(Integer, default=0)


class Database:
    """Класс базы данных с использованием SQLAlchemy ORM"""

    def __init__(self, name: str = "database"):
        self.db_name = name + ".db"
        self.engine = create_engine(f"sqlite:///{self.db_name}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.logger = logging.getLogger("database")
        self.backup_dir = "backups"
        self.dump_interval = int(os.getenv("DUMP_INTERVAL", 3600))
        Path(self.backup_dir).mkdir(exist_ok=True)
        self._start_backup_scheduler()

    def _backup_scheduler(self):
        """Планировщик создания резервных копий"""
        while True:
            time.sleep(self.dump_interval)
            self._create_backup()

    def _create_backup(self):
        """Создает резервную копию базы данных"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.backup_dir}/{self.db_name}_{timestamp}.bak"
        try:
            # Для SQLite просто копируем файл
            with sqlite3.connect(self.db_name) as src:
                with sqlite3.connect(backup_name) as dst:
                    src.backup(dst)
            self.logger.info(f"Создан бэкап: {backup_name}")
        except Exception as e:
            self.logger.info(f"Ошибка при создании бэкапа: {e}")

    def _rotate_backups(self, max_backups=10):
        backups = sorted(glob.glob(f"{self.backup_dir}/*.bak"))
        if len(backups) > max_backups:
            for old_backup in backups[:-max_backups]:
                os.remove(old_backup)

    def _start_backup_scheduler(self):
        """Запускает поток для периодического создания бэкапов"""
        self._rotate_backups()
        thread = threading.Thread(target=self._backup_scheduler, daemon=True)
        thread.start()

    def get_session(self) -> Session:
        """Возвращает новую сессию базы данных"""
        return self.Session()

    def get_all_visitors(self, q: Optional[str | int] = None) -> List[Visitor]:
        """Возвращает всех посетителей с возможностью фильтрации"""
        with self.get_session() as session:
            query = session.query(Visitor)
            if q:
                query = query.filter(
                    or_(Visitor.tg_id.contains(q), Visitor.hash_code.contains(q))
                )
            return query.all()

    def get_all_users(self) -> List[User]:
        """Возвращает всех пользователей"""
        with self.get_session() as session:
            return session.query(User).all()

    def add_user(self, tg_id: str | int) -> bool:
        """Добавляет нового пользователя"""
        with self.get_session() as session:
            if session.query(User).filter(User.tg_id == tg_id).first():
                return False
            user = User(tg_id=tg_id)
            session.add(user)
            try:
                session.commit()
                self.logger.info(f"Добавлен пользователь {tg_id}")
                return True
            except Exception as e:
                session.rollback()
                self.logger.error(f"Ошибка добавления пользователя: {e}")
                return False

    @overload
    def enable_visitor(
        self,
        *,
        tg_id: Optional[int | str] = None,
        to_datetime: Optional[datetime | date] = None,
    ) -> str: ...
    @overload
    def enable_visitor(
        self,
        *,
        hash_code: str | None = None,
    ) -> str: ...

    def enable_visitor(
        self,
        *,
        tg_id: Optional[int | str] = None,
        to_datetime: Optional[datetime | date] = None,
        hash_code: Optional[str] = None,
    ) -> str:
        visitor: Optional[Visitor] = None
        with self.get_session() as session:
            if hash_code:
                visitor = (
                    session.query(Visitor)
                    .filter(Visitor.hash_code == hash_code)
                    .first()
                )
            elif tg_id and to_datetime:
                visitor = (
                    session.query(Visitor)
                    .filter(Visitor.tg_id == tg_id, Visitor.to_datetime == to_datetime)
                    .first()
                )

            else:
                raise ValueError("Не предоставлено нужных аргументов")
            if visitor:
                visitor.is_active = True
                session.commit()
                return str(visitor.hash_code)
        raise sqlite3.Error("Ошибка создания пользователя")

    def reg_new_visitor(
        self, tg_id: str | int, to_datetime: datetime, is_active: bool = True
    ) -> str:
        """Регистрирует нового посетителя"""
        with self.get_session() as session:
            event_date = to_datetime.date()

            if (
                session.query(Visitor)
                .filter(
                    Visitor.tg_id == tg_id,
                    Visitor.to_datetime == event_date,
                    Visitor.is_active is is_active,
                )
                .first()
            ):
                raise AttributeError("Пользователь уже зарегистрирован")

            # Генерация хэша
            hash_code = Utils.generate_hash(tg_id, datetime.now())
            visitor = Visitor(
                tg_id=tg_id,
                to_datetime=event_date,
                hash_code=hash_code,
                is_active=is_active,
            )

            # Обновление счетчика регистраций
            registration = (
                session.query(Registration)
                .filter(Registration.date == event_date)
                .first()
            )

            if not registration:
                raise ValueError("Событие не существует")

            if bool(registration.visitors_count >= registration.max_visitors):
                raise ValueError("Событие переполнено")

            session.add_all([visitor, registration])
            try:
                session.commit()
                return hash_code
            except Exception as e:
                session.rollback()
                self.logger.error(f"Ошибка регистрации: {e}")
                raise

    def delete_visitor(self, tg_id: str | int, to_datetime: Optional[date] = None):
        """Удаляет посетителя"""
        with self.get_session() as session:
            query = session.query(Visitor).filter(Visitor.tg_id == tg_id)
            if to_datetime:
                query = query.filter(Visitor.to_datetime == to_datetime)
            visitors = query.all()

            for visitor in visitors:
                registration = (
                    session.query(Registration)
                    .filter(Registration.date == visitor.to_datetime)
                    .first()
                )
                if registration:
                    registration.visitors_count -= 1
                    session.add(registration)

            query.delete()
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                self.logger.error(f"Ошибка удаления: {e}")
                raise

    def disable_visitor(self, hash_code: str) -> bool:
        """Деактивирует посетителя"""
        with self.get_session() as session:
            visitor = (
                session.query(Visitor).filter(Visitor.hash_code == hash_code).first()
            )

            if not visitor:
                return False

            visitor.is_active = False
            registration = (
                session.query(Registration)
                .filter(Registration.date == visitor.to_datetime)
                .first()
            )

            if registration:
                registration.visitors_count = (
                    session.query(func.count(Visitor.id))
                    .filter(
                        Visitor.to_datetime == visitor.to_datetime,
                        Visitor.is_active is True,
                    )
                    .scalar()
                )
                session.add_all([visitor, registration])
                try:
                    session.commit()
                    return True
                except Exception as e:
                    session.rollback()
                    self.logger.error(f"Ошибка деактивации: {e}")
                    return False
            return False

    def check_registration_by_hash(
        self, hash_code: str, is_strict: bool = True
    ) -> Optional[Visitor]:
        """Проверяет регистрацию по хэшу"""
        with self.get_session() as session:
            query = session.query(Visitor)
            if is_strict:
                result = query.filter(Visitor.hash_code == hash_code)
            else:
                result = query.filter(Visitor.hash_code.like(hash_code))
            return result.first()

    def check_registration_by_tgid(
        self, tg_id: str | int, to_datetime: date, is_active: bool = True
    ) -> bool:
        """Проверяет регистрацию по TG ID"""
        with self.get_session() as session:
            return (
                session.query(Visitor)
                .filter(
                    Visitor.tg_id == tg_id,
                    Visitor.to_datetime == to_datetime,
                    Visitor.is_active == is_active,
                )
                .first()
                is not None
            )

    def get_available(self, date: str | date | Column[date]) -> int:
        with self.get_session() as session:
            query = (
                session.query(Registration).filter(Registration.date == date).first()
            )
            if query:
                max_visitors = int(query.max_visitors.__str__())
            else:
                max_visitors = 230
            query = session.query(Visitor)
            visitors = len(query.filter(Visitor.to_datetime == date).all())

            return int(max_visitors - visitors)

    def get_events(
        self, show_all: bool = False, show_old: bool = True
    ) -> List[Registration]:
        """Возвращает список событий"""
        with self.get_session() as session:
            query = session.query(Registration)

            if not show_all:
                query = query.filter(
                    Registration.visitors_count < Registration.max_visitors
                )
            if not show_old:
                query = query.filter(Registration.date >= date.today())
            return query.order_by(Registration.date).all()

    def is_event_full(self, to_datetime: date) -> bool:
        """Проверяет заполнено ли событие"""
        with self.get_session() as session:
            registration = (
                session.query(Registration)
                .filter(Registration.date == to_datetime)
                .first()
            )
            if registration:
                return bool(registration.visitors_count >= registration.max_visitors)
            else:
                return True

    def add_event(self, to_datetime: date, max_visitors: int):
        """Добавляет или обновляет событие"""
        with self.get_session() as session:
            registration = (
                session.query(Registration)
                .filter(Registration.date == to_datetime)
                .first()
            )

            if registration:
                registration.max_visitors = max_visitors
            else:
                session.add(Registration(date=to_datetime, max_visitors=max_visitors))
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                self.logger.error(f"Ошибка добавления события: {e}")
                raise

    def delete_event(self, to_datetime: date):
        """Удаляет событие"""
        with self.get_session() as session:
            session.query(Visitor).filter(Visitor.to_datetime == to_datetime).delete()

            session.query(Registration).filter(
                Registration.date == to_datetime
            ).delete()

            try:
                session.commit()
            except Exception as e:
                session.rollback()
                self.logger.error(f"Ошибка удаления: {e}")
                raise
