
import bcrypt
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


def init_db() -> None:
    """Создаем таблицы в БД, если их еще нет."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def get_db_session():
    """Простой генератор, который отдает сессию и закрывает ее потом."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AdminUserModel(Base):
    """Модель администратора в базе данных."""
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # Хешированный пароль
    role = Column(String(20), nullable=False, default="admin")  # admin, moderator
    is_active = Column(String(1), nullable=False, default="1")  # 1 - активен, 0 - заблокирован
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def set_password(self, password: str) -> None:
        """Устанавливает хешированный пароль."""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """Проверяет пароль."""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))


@dataclass
class AdminUser:
    # Простая структура для хранения логина и пароля админа (для обратной совместимости)
    username: str
    password: str


def get_admin_user() -> AdminUser:
    """Возвращаем дефолтного админа для обратной совместимости."""
    return AdminUser(username="admin", password="admin123")


def create_default_admin() -> None:
    """Создает дефолтного администратора, если его нет в базе."""
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже админы
        admin_count = db.execute(select(func.count()).select_from(AdminUserModel)).scalar()
        if admin_count == 0:
            # Создаем дефолтного админа
            default_admin = AdminUserModel(username="admin")
            default_admin.set_password("admin123")  # Временный пароль
            db.add(default_admin)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Ошибка при создании дефолтного админа: {e}")
    finally:
        db.close()


def authenticate_admin(username: str, password: str) -> AdminUserModel | None:
    """Аутентифицирует администратора."""
    db = SessionLocal()
    try:
        admin = db.execute(
            select(AdminUserModel).where(
                AdminUserModel.username == username,
                AdminUserModel.is_active == "1"
            )
        ).scalar_one_or_none()

        if admin and admin.check_password(password):
            return admin
        return None
    finally:
        db.close()




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


