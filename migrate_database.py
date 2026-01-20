#!/usr/bin/env python3
"""
Скрипт для миграции базы данных с старой схемы на новую
"""

import sqlite3
import sys
import os

def migrate_students_table():
    """Мигрировать таблицу students на новую схему с foreign key."""

    print("Начинаем миграцию таблицы students...")

    # Подключаемся к базе данных
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()

    try:
        # Шаг 1: Добавляем новую колонку school_class_id
        print("Добавляем колонку school_class_id...")
        cursor.execute("""
            ALTER TABLE students
            ADD COLUMN school_class_id INTEGER REFERENCES school_classes(id)
        """)

        # Шаг 2: Создаем маппинг class_name -> school_class_id
        print("Создаем маппинг классов...")

        # Получаем все существующие классы
        cursor.execute("""
            SELECT sc.id, g.grade_number, sc.class_letter, sc.class_name
            FROM school_classes sc
            JOIN grades g ON sc.grade_id = g.id
        """)
        classes = cursor.fetchall()

        # Создаем словарь для маппинга
        class_mapping = {}
        for class_id, grade_num, class_letter, class_name in classes:
            # class_name в старом формате, например "10А"
            key = f"{grade_num}{class_letter}"
            class_mapping[key] = class_id
            print(f"  {key} -> {class_id}")

        # Шаг 3: Обновляем существующих учеников
        print("Обновляем данные учеников...")

        cursor.execute("SELECT id, class_name FROM students")
        students = cursor.fetchall()

        for student_id, old_class_name in students:
            if old_class_name in class_mapping:
                new_class_id = class_mapping[old_class_name]
                cursor.execute("""
                    UPDATE students
                    SET school_class_id = ?
                    WHERE id = ?
                """, (new_class_id, student_id))
                print(f"  Ученик {student_id}: {old_class_name} -> class_id {new_class_id}")
            else:
                print(f"  Предупреждение: Не найден класс для ученика {student_id}: {old_class_name}")

        # Шаг 4: Удаляем старые колонки
        print("Удаляем старые колонки...")

        # В SQLite нельзя просто удалить колонки, нужно пересоздать таблицу
        cursor.execute("""
            CREATE TABLE students_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_class_id INTEGER NOT NULL REFERENCES school_classes(id),
                full_name VARCHAR(255) NOT NULL,
                achievements TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Копируем данные
        cursor.execute("""
            INSERT INTO students_new (id, school_class_id, full_name, achievements, created_at)
            SELECT id, school_class_id, full_name, achievements, created_at
            FROM students
            WHERE school_class_id IS NOT NULL
        """)

        # Заменяем таблицу
        cursor.execute("DROP TABLE students")
        cursor.execute("ALTER TABLE students_new RENAME TO students")

        # Шаг 5: Создаем индексы для новой схемы
        print("Создаем индексы для новой схемы...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_school_class_id ON students(school_class_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_full_name ON students(full_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_created_at ON students(created_at DESC)")

        # Сохраняем изменения
        conn.commit()

        print("Миграция завершена успешно!")

        # Проверяем результат
        cursor.execute("PRAGMA table_info(students)")
        columns = cursor.fetchall()
        print("Новая схема таблицы students:")
        for col in columns:
            print(f"  {col[1]}: {col[2]} {'NOT NULL' if col[3] else ''}")

        cursor.execute("SELECT COUNT(*) FROM students")
        count = cursor.fetchone()[0]
        print(f"Всего учеников после миграции: {count}")

    except Exception as e:
        print(f"Ошибка при миграции: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """Основная функция миграции."""
    print("Запуск миграции базы данных...")

    # Проверяем наличие файла базы данных
    if not os.path.exists('app.db'):
        print("Файл базы данных app.db не найден!")
        sys.exit(1)

    try:
        migrate_students_table()
        print("Миграция завершена успешно!")
    except Exception as e:
        print(f"Критическая ошибка миграции: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()