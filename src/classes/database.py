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
from pyrogram.types import User as TGUser
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
    is_active = Column(Boolean, default=True)
    is_used = Column(Boolean, default=False)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(String, nullable=False, unique=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=False)
    full_name = Column(String, nullable=False)


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
        self.logger.info("Запуск планировщика резервного копирования")
        while True:
            time.sleep(self.dump_interval)
            with self.get_session() as session:
                session.query(Visitor).filter(Visitor.is_active).delete()
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

    def _rotate_backups(self, max_backups: int = 10):
        """Удаляет старые резервные копии, если их больше max_backups"""
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
        """Возвращает всех посетителей с возможностью фильтрации по tg_id или hash_code"""
        self.logger.info(f"Получение всех посетителей, фильтр: {q}")
        with self.get_session() as session:
            query = session.query(Visitor)
            if q:
                query = query.filter(
                    or_(Visitor.tg_id.contains(q), Visitor.hash_code.contains(q))
                )
            return query.all()

    def get_user_hashcode(self, tg_id: str | int, to_datetime: date | datetime) -> str:
        """Получает hash_code пользователя по tg_id и дате события"""
        self.logger.info(
            f"Получение hash_code для пользователя {tg_id} на {to_datetime}"
        )
        with self.get_session() as session:
            query = session.query(Visitor).filter(
                Visitor.tg_id == tg_id, Visitor.to_datetime == to_datetime
            )
            if query:
                return query.first()
            raise ValueError(
                f"Пользователь {tg_id} не зарегистрирован на {to_datetime}"
            )

    def get_all_users(self) -> List[User]:
        """Возвращает всех пользователей"""
        self.logger.info("Получение всех пользователей")
        with self.get_session() as session:
            return session.query(User).all()

    def add_user(self, user: TGUser) -> bool:
        tg_id = user.id
        """Добавляет нового пользователя по tg_id"""
        self.logger.info(f"Добавление пользователя {tg_id}")
        with self.get_session() as session:
            if session.query(User).filter(User.tg_id == tg_id).first():
                return False
            user = User(
                tg_id=tg_id,
                username=user.username,
                first_name=user.first_name,
                full_name=user.full_name,
            )
            session.add(user)
            try:
                session.commit()
                self.logger.info(f"Добавлен пользователь {tg_id}")
                return True
            except Exception as e:
                session.rollback()
                self.logger.error(f"Ошибка добавления пользователя: {e}")
                return False

    def use_hash(self, hash_code: str) -> bool:
        """Помечает hash_code как использованный"""
        self.logger.info(f"Использование hash_code: {hash_code}")
        with self.get_session() as session:
            visitor = (
                session.query(Visitor)
                .filter(Visitor.hash_code == hash_code, Visitor.is_active.is_(True))
                .first()
            )

            if visitor:
                if bool(visitor.is_active) and not bool(visitor.is_used):
                    visitor.is_used = True
                    session.add(visitor)
                    session.commit()
                else:
                    raise ValueError("Хеш уже был использован")

            return bool(visitor.is_used) if visitor else False

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
        """Активирует посетителя по tg_id и дате или по hash_code"""
        self.logger.info(
            f"Активируем посетителя: tg_id={tg_id}, to_datetime={to_datetime}, hash_code={hash_code}"
        )
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
        """Регистрирует нового посетителя на событие"""
        self.logger.info(
            f"Регистрация нового посетителя: tg_id={tg_id}, to_datetime={to_datetime}, is_active={is_active}"
        )
        with self.get_session() as session:
            event_date = to_datetime.date()

            if (
                session.query(Visitor)
                .filter(
                    Visitor.tg_id == tg_id,
                    Visitor.to_datetime == event_date,
                    Visitor.is_active == is_active,
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
        """Удаляет посетителя по tg_id и (опционально) дате события"""
        self.logger.info(
            f"Удаление посетителя: tg_id={tg_id}, to_datetime={to_datetime}"
        )
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
        """Деактивирует посетителя по hash_code"""
        self.logger.info(f"Деактивация посетителя с hash_code={hash_code}")
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
                        Visitor.is_active,
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
        """Проверяет регистрацию по хэшу (строгое/нестрогое совпадение)"""
        self.logger.info(
            f"Проверка регистрации по hash_code={hash_code}, is_strict={is_strict}"
        )
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
        """Проверяет регистрацию по TG ID и дате события"""
        self.logger.info(
            f"Проверка регистрации по tg_id={tg_id}, to_datetime={to_datetime}, is_active={is_active}"
        )
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
        """Возвращает количество доступных мест на событие"""
        self.logger.info(f"Получение количества доступных мест на дату {date}")
        with self.get_session() as session:
            query = (
                session.query(Registration).filter(Registration.date == date).first()
            )
            if query:
                max_visitors = int(query.max_visitors.__str__())
            else:
                max_visitors = 230
            query = session.query(Visitor)
            visitors = len(
                query.filter(Visitor.to_datetime == date, Visitor.is_active).all()
            )

            return int(max_visitors - visitors)

    def get_events(
        self, show_all: bool = False, show_old: bool = True
    ) -> List[Registration]:
        """Возвращает список событий (опционально: все/только новые/только с местами)"""
        self.logger.info(f"Получение событий: show_all={show_all}, show_old={show_old}")
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
        """Проверяет заполнено ли событие на дату"""
        self.logger.info(f"Проверка заполненности события на дату {to_datetime}")
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
        """Добавляет или обновляет событие с максимальным числом участников"""
        self.logger.info(
            f"Добавление/обновление события: дата={to_datetime}, макс. участников={max_visitors}"
        )
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
        """Удаляет событие и всех связанных посетителей по дате"""
        self.logger.info(f"Удаление события на дату {to_datetime}")
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
