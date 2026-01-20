#!/usr/bin/env python3
"""
Скрипт для проверки состояния базы данных и создания администратора
"""

import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database import init_db, create_default_admin, authenticate_admin, SessionLocal, select, AdminUserModel

    def main():
        print("🔍 Проверка базы данных...")

        # Инициализируем базу данных
        print("📦 Инициализация базы данных...")
        init_db()

        # Создаем дефолтного админа
        print("👤 Создание дефолтного администратора...")
        create_default_admin()

        # Проверяем администраторов
        db = SessionLocal()
        try:
            admins = db.execute(select(AdminUserModel)).scalars().all()
            print(f"📊 Найдено администраторов: {len(admins)}")

            for admin in admins:
                print(f"   - {admin.username} (роль: {admin.role}, активен: {'да' if admin.is_active == '1' else 'нет'})")

            # Проверяем аутентификацию
            print("\n🔐 Проверка аутентификации...")
            test_admin = authenticate_admin("admin", "admin123")
            if test_admin:
                print("✅ Аутентификация успешна")
            else:
                print("❌ Аутентификация не удалась")

        except Exception as e:
            print(f"❌ Ошибка при проверке: {e}")
        finally:
            db.close()

        print("\n✅ Проверка завершена!")

    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что виртуальное окружение активировано и зависимости установлены")
    sys.exit(1)