

import os
from flask import Flask, redirect, render_template, request, session, url_for

from database import (
    Registration,
    Student,
    get_admin_user,
    get_db_session,
    init_db,
    search_registrations,
    search_students,
)


def create_app():
    # Создаем приложение Flask
    app = Flask(__name__)
    # Ключ для сессий и flash-сообщений (в реальности возьмите из переменных окружения)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

    # Создаем таблицы (если их еще нет)
    init_db()

    # Главная: список карточек учеников (публичный просмотр)
    @app.route("/", methods=["GET"])
    def index():
        q = request.args.get("q")
        class_name = request.args.get("class")

        with next(get_db_session()) as db:
            students = search_students(db, query=q, class_name=class_name)

        return render_template("index.html", students=students, q=q or "", class_name=class_name or "")

    # Страница входа для админа
    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            # Берем дефолтного пользователя (можно переопределить через переменные окружения ниже)
            admin = get_admin_user()

            
            user = "admin"
            passw = "12345"
            
            admin.username = user
            admin.password = passw

            # Простейшая проверка логина/пароля
            if username == admin.username and password == admin.password:
                session["admin_authenticated"] = True
                return redirect(url_for("admin_dashboard"))

            # Если данные неверные — просто показываем страницу с текстом ошибки
            return render_template("admin_login.html", error_message="Неверные учетные данные")

        return render_template("admin_login.html")

    # Выход из админ-панели
    @app.route("/admin/logout")
    def admin_logout():
        session.pop("admin_authenticated", None)
        return redirect(url_for("admin_login"))

    # Простая проверка, что пользователь залогинен как админ
    def require_admin():
        if not session.get("admin_authenticated"):
            return redirect(url_for("admin_login"))
        return None

    # Админ-панель: список учеников + поиск/фильтр/сортировки
    @app.route("/admin", methods=["GET"])
    def admin_dashboard():
        redirect_resp = require_admin()
        if redirect_resp:
            return redirect_resp

        # Параметры из строки запроса
        q = request.args.get("q")  # поиск по ФИО
        class_name = request.args.get("class")  # фильтр по классу
        order = request.args.get("order")  # сортировка
        order_by_class = order == "class"
        order_by_teacher = order == "teacher"

        # Получаем записи из базы через вспомогательную функцию
        with next(get_db_session()) as db:
            students = search_students(
                db,
                query=q,
                class_name=class_name,
                order_by_class=order_by_class,
                order_by_teacher=order_by_teacher,
            )

            # Списки для фильтров (классы и кл.руководители)
            from sqlalchemy import select
            class_stmt = select(Student.class_name).distinct().order_by(Student.class_name.asc())
            teacher_stmt = select(Student.class_teacher).distinct().order_by(Student.class_teacher.asc())
            classes = [row[0] for row in db.execute(class_stmt).all()]
            teachers = [row[0] for row in db.execute(teacher_stmt).all()]

        # Рендерим шаблон и передаем данные
        return render_template(
            "admin_dashboard.html",
            students=students,
            q=q or "",
            class_name=class_name or "",
            order=order or "",
            classes=classes,
            teachers=teachers,
        )

    # Создание карточки ученика (админ)
    @app.route("/admin/students/new", methods=["GET", "POST"])
    def admin_student_new():
        redirect_resp = require_admin()
        if redirect_resp:
            return redirect_resp

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            class_name = request.form.get("class_name", "").strip()
            class_teacher = request.form.get("class_teacher", "").strip()
            achievements = request.form.get("achievements", "").strip()

            if not (full_name and class_name and class_teacher):
                return render_template("admin_student_form.html", error_message="Заполните все обязательные поля.")

            with next(get_db_session()) as db:
                s = Student(
                    full_name=full_name,
                    class_name=class_name,
                    class_teacher=class_teacher,
                    achievements=achievements or None,
                )
                db.add(s)
                db.commit()

            return redirect(url_for("admin_dashboard", ok=1))

        return render_template("admin_student_form.html")

    # Редактирование карточки ученика (админ)
    @app.route("/admin/students/<int:student_id>/edit", methods=["GET", "POST"])
    def admin_student_edit(student_id: int):
        redirect_resp = require_admin()
        if redirect_resp:
            return redirect_resp

        with next(get_db_session()) as db:
            student = db.get(Student, student_id)
            if not student:
                return redirect(url_for("admin_dashboard"))

            if request.method == "POST":
                full_name = request.form.get("full_name", "").strip()
                class_name = request.form.get("class_name", "").strip()
                class_teacher = request.form.get("class_teacher", "").strip()
                achievements = request.form.get("achievements", "").strip()

                if not (full_name and class_name and class_teacher):
                    return render_template(
                        "admin_student_form.html",
                        error_message="Заполните все обязательные поля.",
                        student=student,
                    )

                student.full_name = full_name
                student.class_name = class_name
                student.class_teacher = class_teacher
                student.achievements = achievements or None
                db.commit()

                return redirect(url_for("admin_dashboard", ok=1))

        return render_template("admin_student_form.html", student=student)

    return app


# Создаем приложение (так проще запускать через python app.py)
app = create_app()


if __name__ == "__main__":
    # Запускаем локальный сервер разработчика
    app.run(debug=True)


