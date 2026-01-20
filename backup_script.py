#!/usr/bin/env python3
"""
Скрипт для автоматического создания бэкапов базы данных.
Можно запускать по расписанию через cron или планировщик задач.

Пример для cron (Linux):
0 2 * * * cd /path/to/project && python3 backup_script.py

Пример для планировщика задач Windows:
schtasks /create /tn "StudentDB Backup" /tr "python3 C:\path\to\project\backup_script.py" /sc daily /st 02:00
"""

import sys
import os
from datetime import datetime

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database import create_database_backup, cleanup_old_backups

    def main():
        """Основная функция создания бэкапа."""
        try:
            print(f"[{datetime.now()}] Начинаем создание бэкапа...")

            # Создаем бэкап
            backup_path = create_database_backup()

            print(f"[{datetime.now()}] Бэкап успешно создан: {backup_path}")

            # Очищаем старые бэкапы (оставляем 30 дней)
            cleanup_old_backups(keep_count=30)
            print(f"[{datetime.now()}] Очистка старых бэкапов завершена")

            return True

        except Exception as e:
            print(f"[{datetime.now()}] Ошибка при создании бэкапа: {e}")
            return False

    if __name__ == "__main__":
        success = main()
        sys.exit(0 if success else 1)

except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что скрипт запускается из директории проекта")
    sys.exit(1)