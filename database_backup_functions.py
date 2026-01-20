import shutil
import os
from datetime import datetime


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