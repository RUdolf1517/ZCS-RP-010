"""
Простой модуль работы с базой данных.
Тут мы настраиваем SQLite и описываем таблицу заявок.
Комментарии написаны максимально просто.
"""

from dataclasses import dataclass

# Импортируем нужные классы из SQLAlchemy
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, func, select, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker


# Создаем базовый класс для моделей
Base = declarative_base()


def get_engine(db_url: str = "sqlite:///app.db"):
    # Создаем подключение к SQLite. future=True для нового стиля API
    return create_engine(db_url, echo=False, future=True)


# Фабрика сессий. Через нее будем получать доступ к БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


class Registration(Base):
    """Модель заявки на мероприятие."""

    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)  # айди заявки
    full_name = Column(String(255), nullable=False, index=True)  # ФИО
    email = Column(String(255), nullable=False, index=True)  # email
    phone = Column(String(50), nullable=False)  # телефон
    school = Column(String(255), nullable=True)  # школа/организация (опционально)
    supervisor = Column(String(255), nullable=False, index=True)  # руководитель
    comment = Column(String(1000), nullable=True)  # комментарий
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # когда создано


def init_db() -> None:
    """Создаем таблицы в БД, если их еще нет."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    # Пробуем добавить столбец school, если таблица уже существовала без него
    with engine.connect() as conn:
        try:
            info = conn.execute(text("PRAGMA table_info(registrations)"))
            cols = {row[1] for row in info.fetchall()}  # второе поле — имя столбца
            if "school" not in cols:
                conn.execute(text("ALTER TABLE registrations ADD COLUMN school VARCHAR(255)"))
        except Exception:
            # Если что-то пошло не так, просто пропускаем (для простоты)
            pass


def get_db_session():
    """Простой генератор, который отдает сессию и закрывает ее потом."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@dataclass
class AdminUser:
    # Простая структура для хранения логина и пароля админа
    username: str
    password: str  # В реальном проекте тут должен быть хеш пароля


def get_admin_user() -> AdminUser:
    """Возвращаем дефолтного админа. Можно переопределить через переменные окружения в app.py."""
    return AdminUser(username="admin", password="admin123")


def search_registrations(
    db: Session,
    query: str | None = None,
    supervisor: str | None = None,
    order_by_supervisor: bool = False,
    order_by_school: bool = False,
):
    """
    Ищем заявки. Фильтрация по строке (ФИО или email) и по руководителю.
    Сортировка либо по руководителю, либо просто по дате создания.
    Используется ORM, поэтому защищено от SQL-инъекций.
    """
    stmt = select(Registration)

    if query:
        like = f"%{query.strip()}%"
        stmt = stmt.where((Registration.full_name.ilike(like)) | (Registration.email.ilike(like)))

    if supervisor:
        stmt = stmt.where(Registration.supervisor == supervisor)

    if order_by_supervisor:
        stmt = stmt.order_by(Registration.supervisor.asc(), Registration.created_at.desc())
    elif order_by_school:
        stmt = stmt.order_by(Registration.school.asc(), Registration.created_at.desc())
    else:
        stmt = stmt.order_by(Registration.created_at.desc())

    return db.execute(stmt).scalars().all()


class Student(Base):
    """Модель ученика с достижениями."""

    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False, index=True)  # ФИО ученика
    class_name = Column(String(50), nullable=False, index=True)  # Класс (например: 7А)
    class_teacher = Column(String(255), nullable=False, index=True)  # Кл. руководитель
    achievements = Column(Text, nullable=True)  # Текст с достижениями
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def search_students(
    db: Session,
    *,
    query: str | None = None,
    class_name: str | None = None,
    order_by_class: bool = False,
    order_by_teacher: bool = False,
):
    """Поиск учеников по ФИО, фильтр по классу и сортировка."""
    stmt = select(Student)

    if query:
        like = f"%{query.strip()}%"
        stmt = stmt.where(Student.full_name.ilike(like))

    if class_name:
        stmt = stmt.where(Student.class_name == class_name)

    if order_by_class:
        stmt = stmt.order_by(Student.class_name.asc(), Student.full_name.asc())
    elif order_by_teacher:
        stmt = stmt.order_by(Student.class_teacher.asc(), Student.full_name.asc())
    else:
        stmt = stmt.order_by(Student.created_at.desc())

    return db.execute(stmt).scalars().all()


