"""Модуль базы данных с использованием SQLAlchemy"""

import logging
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (Boolean, Column, Date, Integer, String, create_engine,
                        func, or_)
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


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(String, nullable=False, unique=True)


class Registration(Base):
    __tablename__ = "registrations"
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, unique=True)
    max_visitors = Column(Integer, nullable=False)
    visitors_count = Column(Integer, default=0)


class Database:
    """Класс базы данных с использованием SQLAlchemy ORM"""

    def __init__(self, name: str = "database"):
        self.engine = create_engine(f"sqlite:///{name}.db")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.logger = logging.getLogger("database")

    def get_session(self) -> Session:
        """Возвращает новую сессию базы данных"""
        return self.Session()

    def get_all_visitors(self, q: Optional[str] = None) -> List[Visitor]:
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

    def add_user(self, tg_id: str) -> bool:
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

    def reg_new_visitor(self, tg_id: str | int, to_datetime: datetime) -> str:
        """Регистрирует нового посетителя"""
        with self.get_session() as session:
            event_date = to_datetime.date()

            # Проверка существующей регистрации
            if (
                session.query(Visitor)
                .filter(
                    Visitor.tg_id == tg_id,
                    Visitor.to_datetime == event_date,
                    Visitor.is_active == True,
                )
                .first()
            ):
                raise AttributeError("Пользователь уже зарегистрирован")

            # Генерация хэша
            hash_code = Utils.generate_hash(tg_id, datetime.now())
            visitor = Visitor(tg_id=tg_id, to_datetime=event_date, hash_code=hash_code)

            # Обновление счетчика регистраций
            registration = (
                session.query(Registration)
                .filter(Registration.date == event_date)
                .first()
            )

            if not registration:
                raise ValueError("Событие не существует")

            if registration.visitors_count >= registration.max_visitors:
                raise ValueError("Событие переполнено")

            registration.visitors_count += 1
            session.add_all([visitor, registration])
            try:
                session.commit()
                return hash_code
            except Exception as e:
                session.rollback()
                self.logger.error(f"Ошибка регистрации: {e}")
                raise

    def delete_visitor(self, tg_id: str, to_datetime: Optional[date] = None):
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
                        Visitor.is_active == True,
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

    def get_available_slots(self, to_datetime: date) -> int:
        """Возвращает количество свободных мест"""
        with self.get_session() as session:
            registration = (
                session.query(Registration)
                .filter(Registration.date == to_datetime)
                .first()
            )
            return (
                registration.max_visitors - registration.visitors_count
                if registration
                else 0
            )

    def check_registration_by_hash(self, hash_code: str) -> Optional[Visitor]:
        """Проверяет регистрацию по хэшу"""
        with self.get_session() as session:
            return session.query(Visitor).filter(Visitor.hash_code == hash_code).first()

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
            return (
                registration.visitors_count >= registration.max_visitors
                if registration
                else True
            )

    def add_event(self, date: date, max_visitors: int):
        """Добавляет или обновляет событие"""
        with self.get_session() as session:
            registration = (
                session.query(Registration).filter(Registration.date == date).first()
            )

            if registration:
                registration.max_visitors = max_visitors
            else:
                session.add(Registration(date=date, max_visitors=max_visitors))
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                self.logger.error(f"Ошибка добавления события: {e}")
                raise

    def delete_event(self, date: date):
        """Удаляет событие"""
        with self.get_session() as session:
            session.query(Visitor).filter(Visitor.to_datetime == date).delete()

            session.query(Registration).filter(Registration.date == date).delete()

            try:
                session.commit()
            except Exception as e:
                session.rollback()
                self.logger.error(f"Ошибка удаления: {e}")
                raise
