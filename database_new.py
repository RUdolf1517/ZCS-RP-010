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
    """Создаем таблицы в БД, если их еще нет и оптимизируем."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    # Оптимизация базы данных для SQLite
    with engine.connect() as conn:
        # Включаем WAL режим для лучшей производительности
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA synchronous=NORMAL"))
        conn.execute(text("PRAGMA cache_size=-64000"))  # 64MB кэш
        conn.execute(text("PRAGMA temp_store=MEMORY"))

        # Создаем дополнительные индексы для оптимизации поиска
        try:
            # Индекс для поиска по классу + имени
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_students_class_name_full_name ON students(class_name, full_name)"))
            # Индекс для поиска по учителю
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_students_class_teacher ON students(class_teacher)"))
            # Индекс для поиска по дате создания (для сортировки)
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_students_created_at ON students(created_at DESC)"))
        except Exception as e:
            print(f"Предупреждение при создании индексов: {e}")

        conn.commit()


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
    achievements = Column(Text, nullable=True)  # JSON с достижениями
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Оптимизация для SQLite
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __init__(self, **kwargs):
        # Валидация данных при создании
        if 'full_name' in kwargs:
            kwargs['full_name'] = kwargs['full_name'].strip()
            if len(kwargs['full_name']) < 2:
                raise ValueError("ФИО должно содержать минимум 2 символа")

        if 'class_name' in kwargs:
            kwargs['class_name'] = kwargs['class_name'].strip()
            if not kwargs['class_name']:
                raise ValueError("Класс не может быть пустым")

        if 'class_teacher' in kwargs:
            kwargs['class_teacher'] = kwargs['class_teacher'].strip()
            if len(kwargs['class_teacher']) < 2:
                raise ValueError("ФИО классного руководителя должно содержать минимум 2 символа")

        super().__init__(**kwargs)


def search_students(
    db: Session,
    *,
    query: str | None = None,
    class_name: str | None = None,
    order_by_class: bool = False,
    order_by_teacher: bool = False,
    limit: int | None = None,
    offset: int | None = None,
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

    if limit:
        stmt = stmt.limit(limit)
    if offset:
        stmt = stmt.offset(offset)

    return db.execute(stmt).scalars().all()


def find_similar_students(db: Session, full_name: str, class_name: str) -> list[Student]:
    """Ищет похожих учеников для предупреждения о дублировании."""
    # Разбиваем ФИО на части для более гибкого поиска
    name_parts = full_name.strip().split()
    if not name_parts:
        return []

    # Ищем по совпадению основных частей имени и класса
    similar_students = []

    # Поиск по полному совпадению ФИО и класса
    exact_match = db.execute(
        select(Student).where(
            Student.full_name == full_name.strip(),
            Student.class_name == class_name.strip()
        )
    ).scalars().all()

    if exact_match:
        return exact_match

    # Поиск по частичному совпадению (минимум 2 слова из ФИО)
    if len(name_parts) >= 2:
        for student in db.execute(select(Student).where(Student.class_name == class_name.strip())).scalars():
            student_name_parts = set(student.full_name.lower().split())
            input_name_parts = set(part.lower() for part in name_parts)

            # Если совпадает минимум 2 части имени
            if len(student_name_parts.intersection(input_name_parts)) >= 2:
                similar_students.append(student)

    return similar_students[:5]  # Ограничиваем до 5 результатов