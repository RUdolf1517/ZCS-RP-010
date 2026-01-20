
import bcrypt
import shutil
import os
from datetime import datetime
from dataclasses import dataclass

# Импортируем нужные классы из SQLAlchemy
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, func, select, text, ForeignKey
from sqlalchemy.orm import Session, declarative_base, sessionmaker, relationship


# Создаем базовый класс для моделей
Base = declarative_base()

# Константы ролей пользователей
USER_ROLES = {
    'admin': {'name': 'Администратор', 'description': 'Полный доступ ко всем функциям'},
    'deputy': {'name': 'Завуч', 'description': 'Управление учебным процессом и отчетами'},
    'teacher': {'name': 'Учитель', 'description': 'Управление учениками своего предмета'},
    'class_teacher': {'name': 'Классный руководитель', 'description': 'Управление классом и учениками'}
}

# Права доступа для ролей
ROLE_PERMISSIONS = {
    'admin': ['create_users', 'edit_users', 'delete_users', 'manage_students', 'import_export', 'backups'],
    'deputy': ['manage_students', 'import_export', 'view_reports', 'edit_students'],
    'teacher': ['view_students', 'edit_own_students', 'add_achievements'],
    'class_teacher': ['manage_class', 'edit_class_students', 'view_reports', 'export_class_reports', 'add_achievements']
}


def get_engine(db_url: str = "sqlite:///app.db"):
    # Создаем подключение к SQLite. future=True для нового стиля API
    return create_engine(db_url, echo=False, future=True)


# Фабрика сессий. Через нее будем получать доступ к БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def init_db() -> None:
    """Создаем таблицы в БД, если их еще нет и оптимизируем."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    # Создаем тестовую параллель для демонстрации (если таблица пустая)
    create_demo_grade_if_empty()

    # Оптимизация базы данных для SQLite
    with engine.connect() as conn:
        # Включаем WAL режим для лучшей производительности
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA synchronous=NORMAL"))
        conn.execute(text("PRAGMA cache_size=-64000"))  # 64MB кэш
        conn.execute(text("PRAGMA temp_store=MEMORY"))

        # Создаем дополнительные индексы для оптимизации поиска
        try:
            # Индекс для поиска по классу
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_students_school_class_id ON students(school_class_id)"))
            # Индекс для поиска по имени ученика
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_students_full_name ON students(full_name)"))
            # Индекс для поиска по дате создания
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_students_created_at ON students(created_at DESC)"))
            # Индексы для классов
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_school_classes_grade_id ON school_classes(grade_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_school_classes_class_name ON school_classes(class_name)"))
        except Exception as e:
            print(f"Предупреждение при создании индексов: {e}")

        conn.commit()


def create_demo_grade_if_empty() -> None:
    """Создать тестовую параллель 10 классов, если база данных пустая."""
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже параллели
        existing_grades = db.execute(select(func.count()).select_from(Grade)).scalar() or 0

        if existing_grades == 0:
            print("Создание тестовой параллели 10 классов...")
            # Создаем параллель 10 классов
            grade = Grade(grade_number=10)
            db.add(grade)
            db.commit()
            db.refresh(grade)

            # Создаем классы А, Б, В для 10 параллели
            for letter in ['А', 'Б', 'В']:
                try:
                    create_school_class(db, grade.id, letter)
                except ValueError:
                    # Класс уже существует, пропускаем
                    pass

            print("Тестовая параллель создана успешно!")
        else:
            print(f"Найдено {existing_grades} параллелей, тестовая параллель не создается.")

    except Exception as e:
        db.rollback()
        print(f"Ошибка при создании тестовой параллели: {e}")
    finally:
        db.close()


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
    role = Column(String(20), nullable=False, default="admin")  # admin, deputy, teacher, class_teacher
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
    import os

    db = SessionLocal()
    try:
        # Проверяем, есть ли уже админы
        admin_count = db.execute(select(func.count()).select_from(AdminUserModel)).scalar()
        if admin_count == 0:
            # Получаем настройки из переменных окружения
            admin_username = os.environ.get("ADMIN_USERNAME", "admin")
            admin_password = os.environ.get("ADMIN_PASSWORD")

            if not admin_password:
                print("WARNING: ADMIN_PASSWORD не установлен! Используйте переменную окружения ADMIN_PASSWORD")
                return

            # Создаем дефолтного админа
            default_admin = AdminUserModel(username=admin_username, role="admin")
            default_admin.set_password(admin_password)
            db.add(default_admin)
            db.commit()
            print(f"Создан администратор: {admin_username}")
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


class Grade(Base):
    """Модель параллели (7 классы, 8 классы и т.д.)"""

    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    grade_number = Column(Integer, nullable=False, unique=True, index=True)  # Номер параллели (7, 8, 9, 10, 11)
    grade_name = Column(String(50), nullable=False)  # Название параллели (7 классы, 8 классы)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Отношение к классам
    classes = relationship("SchoolClass", back_populates="grade", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        if 'grade_number' in kwargs:
            kwargs['grade_name'] = f"{kwargs['grade_number']} классы"
        super().__init__(**kwargs)


class SchoolClass(Base):
    """Модель класса (7А, 8Б и т.д.)"""

    __tablename__ = "school_classes"

    id = Column(Integer, primary_key=True, index=True)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False, index=True)
    class_letter = Column(String(10), nullable=False)  # Буква класса (А, Б, В, Г)
    class_name = Column(String(50), nullable=False, unique=True, index=True)  # Полное имя (7А, 8Б)
    class_teacher_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)  # Классный руководитель
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Отношения
    grade = relationship("Grade", back_populates="classes")
    class_teacher = relationship("AdminUserModel", foreign_keys=[class_teacher_id])
    students = relationship("Student", back_populates="school_class", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        if 'grade_id' in kwargs and 'class_letter' in kwargs:
            # Найдем номер параллели для создания полного имени класса
            db = SessionLocal()
            try:
                grade = db.get(Grade, kwargs['grade_id'])
                if grade:
                    kwargs['class_name'] = f"{grade.grade_number}{kwargs['class_letter']}"
            finally:
                db.close()
        super().__init__(**kwargs)


class Student(Base):
    """Модель ученика с достижениями."""

    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    school_class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False, index=True)  # ФИО ученика
    achievements = Column(Text, nullable=True)  # JSON с достижениями
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Отношения
    school_class = relationship("SchoolClass", back_populates="students")

    # Оптимизация для SQLite
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    @property
    def class_name(self):
        """Получить полное имя класса (7А, 8Б и т.д.)"""
        return self.school_class.class_name if self.school_class else ""

    @property
    def class_teacher(self):
        """Получить имя пользователя классного руководителя"""
        return self.school_class.class_teacher.username if self.school_class and self.school_class.class_teacher else ""

    def __init__(self, **kwargs):
        # Валидация данных при создании
        if 'full_name' in kwargs:
            kwargs['full_name'] = kwargs['full_name'].strip()
            if len(kwargs['full_name']) < 2:
                raise ValueError("ФИО должно содержать минимум 2 символа")

        super().__init__(**kwargs)


def search_students(
    db: Session,
    *,
    query: str | None = None,
    class_name: str | None = None,
    grade_id: int | None = None,
    school_class_id: int | None = None,
    order_by_class: bool = False,
    order_by_teacher: bool = False,
    limit: int | None = None,
    offset: int | None = None,
):
    """Поиск учеников по ФИО, фильтр по классу/параллели и сортировка."""
    stmt = select(Student).join(SchoolClass).join(Grade)

    if query:
        like = f"%{query.strip()}%"
        stmt = stmt.where(Student.full_name.ilike(like))

    if class_name:
        stmt = stmt.where(SchoolClass.class_name == class_name)

    if grade_id:
        stmt = stmt.where(SchoolClass.grade_id == grade_id)

    if school_class_id:
        stmt = stmt.where(Student.school_class_id == school_class_id)

    if order_by_class:
        stmt = stmt.order_by(SchoolClass.class_name.asc(), Student.full_name.asc())
    elif order_by_teacher:
        stmt = stmt.order_by(SchoolClass.class_teacher_id.asc(), Student.full_name.asc())
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


# Функции для работы с параллелями и классами
def get_all_grades(db: Session) -> list[Grade]:
    """Получить все параллели."""
    return db.execute(select(Grade).order_by(Grade.grade_number)).scalars().all()


def get_classes_by_grade(db: Session, grade_id: int) -> list[SchoolClass]:
    """Получить все классы параллели."""
    return db.execute(
        select(SchoolClass)
        .where(SchoolClass.grade_id == grade_id)
        .order_by(SchoolClass.class_letter)
    ).scalars().all()


def create_grade(db: Session, grade_number: int) -> Grade:
    """Создать параллель."""
    existing = db.execute(select(Grade).where(Grade.grade_number == grade_number)).scalar_one_or_none()
    if existing:
        raise ValueError(f"Параллель {grade_number} уже существует")

    grade = Grade(grade_number=grade_number)
    db.add(grade)
    db.commit()
    db.refresh(grade)
    return grade


def create_school_class(db: Session, grade_id: int, class_letter: str, class_teacher_id: int | None = None) -> SchoolClass:
    """Создать класс."""
    grade = db.get(Grade, grade_id)
    if not grade:
        raise ValueError(f"Параллель с ID {grade_id} не найдена")

    class_name = f"{grade.grade_number}{class_letter}"

    # Проверяем уникальность
    existing = db.execute(select(SchoolClass).where(SchoolClass.class_name == class_name)).scalar_one_or_none()
    if existing:
        raise ValueError(f"Класс {class_name} уже существует")

    school_class = SchoolClass(
        grade_id=grade_id,
        class_letter=class_letter,
        class_name=class_name,
        class_teacher_id=class_teacher_id
    )
    db.add(school_class)
    db.commit()
    db.refresh(school_class)
    return school_class


def update_school_class(db: Session, class_id: int, class_teacher_id: int | None = None) -> SchoolClass:
    """Обновить классного руководителя."""
    school_class = db.get(SchoolClass, class_id)
    if not school_class:
        raise ValueError(f"Класс с ID {class_id} не найден")

    school_class.class_teacher_id = class_teacher_id
    db.commit()
    db.refresh(school_class)
    return school_class


def create_database_backup(backup_dir: str = "backups") -> str:
    """Создает бэкап базы данных."""
    # Создаем директорию для бэкапов, если не существует
    os.makedirs(backup_dir, exist_ok=True)

    # Путь к текущей базе данных
    db_path = "app.db"
    if not os.path.exists(db_path):
        raise FileNotFoundError("База данных не найдена")

    # Создаем имя файла бэкапа с timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"app_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    # Копируем файл базы данных
    shutil.copy2(db_path, backup_path)

    # Очищаем старые бэкапы (оставляем последние 10)
    cleanup_old_backups(backup_dir, keep_count=10)

    return backup_path


def cleanup_old_backups(backup_dir: str, keep_count: int = 10) -> None:
    """Удаляет старые бэкапы, оставляя только последние N."""
    if not os.path.exists(backup_dir):
        return

    # Получаем список файлов бэкапов
    backup_files = [
        os.path.join(backup_dir, f)
        for f in os.listdir(backup_dir)
        if f.startswith("app_backup_") and f.endswith(".db")
    ]

    # Сортируем по времени создания (новые сначала)
    backup_files.sort(key=os.path.getctime, reverse=True)

    # Удаляем старые файлы
    for old_backup in backup_files[keep_count:]:
        try:
            os.remove(old_backup)
        except OSError:
            pass  # Игнорируем ошибки удаления


def get_backup_list(backup_dir: str = "backups") -> list[dict]:
    """Возвращает список доступных бэкапов."""
    if not os.path.exists(backup_dir):
        return []

    backups = []
    for filename in os.listdir(backup_dir):
        if filename.startswith("app_backup_") and filename.endswith(".db"):
            filepath = os.path.join(backup_dir, filename)
            stat = os.stat(filepath)
            backups.append({
                "filename": filename,
                "filepath": filepath,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime),
                "size_human": f"{stat.st_size / 1024:.1f} KB"
            })

    # Сортируем по времени создания (новые сначала)
    backups.sort(key=lambda x: x["created"], reverse=True)
    return backups


def restore_database_from_backup(backup_path: str) -> None:
    """Восстанавливает базу данных из бэкапа."""
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Файл бэкапа не найден: {backup_path}")

    # Создаем бэкап текущей базы перед восстановлением
    current_backup = create_database_backup()

    # Восстанавливаем из бэкапа
    db_path = "app.db"
    shutil.copy2(backup_path, db_path)


def get_all_users(db: Session) -> list[AdminUserModel]:
    """Получает список всех пользователей."""
    return db.execute(select(AdminUserModel).order_by(AdminUserModel.created_at.desc())).scalars().all()


def create_admin_user(db: Session, username: str, password: str, role: str = "class_teacher") -> AdminUserModel:
    """Создает нового администратора."""
    if role not in USER_ROLES:
        raise ValueError(f"Недопустимая роль: {role}")

    # Проверяем, что пользователь не существует
    existing = db.execute(
        select(AdminUserModel).where(AdminUserModel.username == username)
    ).scalar_one_or_none()

    if existing:
        raise ValueError(f"Пользователь с именем {username} уже существует")

    new_user = AdminUserModel(username=username, role=role)
    new_user.set_password(password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def update_admin_user(db: Session, user_id: int, username: str = None, password: str = None, role: str = None, is_active: str = None) -> AdminUserModel:
    """Обновляет данные администратора."""
    user = db.get(AdminUserModel, user_id)
    if not user:
        raise ValueError(f"Пользователь с ID {user_id} не найден")

    if username is not None:
        # Проверяем уникальность имени
        existing = db.execute(
            select(AdminUserModel).where(
                AdminUserModel.username == username,
                AdminUserModel.id != user_id
            )
        ).scalar_one_or_none()
        if existing:
            raise ValueError(f"Пользователь с именем {username} уже существует")
        user.username = username

    if password is not None:
        user.set_password(password)

    if role is not None and role in USER_ROLES:
        user.role = role

    if is_active is not None:
        user.is_active = is_active

    db.commit()
    db.refresh(user)
    return user


def delete_admin_user(db: Session, user_id: int) -> None:
    """Удаляет администратора."""
    user = db.get(AdminUserModel, user_id)
    if not user:
        raise ValueError(f"Пользователь с ID {user_id} не найден")

    # Нельзя удалить последнего администратора
    admin_count = db.execute(
        select(func.count()).select_from(AdminUserModel).where(AdminUserModel.role == "admin")
    ).scalar()

    if user.role == "admin" and admin_count <= 1:
        raise ValueError("Нельзя удалить последнего администратора")

    db.delete(user)
    db.commit()


def check_user_permission(user_role: str, permission: str) -> bool:
    """Проверяет, имеет ли пользователь указанное право."""
    if user_role not in ROLE_PERMISSIONS:
        return False
    return permission in ROLE_PERMISSIONS[user_role]

