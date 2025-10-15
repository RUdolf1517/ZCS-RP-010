import os
import io
from datetime import datetime
from flask import Flask, redirect, render_template, request, session, url_for, send_file
from sqlalchemy import delete, select
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from database import (
    Student,
    get_admin_user,
    get_db_session,
    init_db,
    search_students,
)


def create_app():
    # Создаем приложение Flask
    app = Flask(__name__)
    # Ключ для сессий и flash-сообщений
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
        return True

    # Админ-панель: список учеников + поиск/фильтр/сортировки
    @app.route("/admin", methods=["GET"])
    def admin_dashboard():
        auth_result = require_admin()
        if auth_result != True:
            return auth_result

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
        auth_result = require_admin()
        if auth_result != True:
            return auth_result

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            class_name = request.form.get("class_name", "").strip()
            class_teacher = request.form.get("class_teacher", "").strip()
            # Собираем неограниченное число достижений из массива achievements[]
            achievements_items = request.form.getlist("achievements[]")
            achievements = "\n".join([a.strip() for a in achievements_items if a and a.strip()])

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
        auth_result = require_admin()
        if auth_result != True:
            return auth_result

        with next(get_db_session()) as db:
            student = db.get(Student, student_id)
            if not student:
                return redirect(url_for("admin_dashboard"))

            if request.method == "POST":
                full_name = request.form.get("full_name", "").strip()
                class_name = request.form.get("class_name", "").strip()
                class_teacher = request.form.get("class_teacher", "").strip()
                achievements_items = request.form.getlist("achievements[]")
                achievements = "\n".join([a.strip() for a in achievements_items if a and a.strip()])

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

    # Удаление карточки ученика (админ)
    @app.route("/admin/students/<int:student_id>/delete", methods=["POST"])
    def admin_student_delete(student_id: int):
        auth_result = require_admin()
        if auth_result != True:
            return auth_result

        with next(get_db_session()) as db:
            student = db.get(Student, student_id)
            if student:
                db.delete(student)
                db.commit()
        return redirect(url_for("admin_dashboard"))

    # Экспорт карточек учеников в Excel
    @app.route("/admin/export/excel")
    def admin_export_excel():
        auth_result = require_admin()
        if auth_result != True:
            return auth_result

        with next(get_db_session()) as db:
            students = db.execute(select(Student).order_by(Student.class_name.asc(), Student.full_name.asc())).scalars().all()

        # Создаем Excel файл
        wb = Workbook()
        ws = wb.active
        ws.title = "Карточки учеников"

        # Заголовки
        headers = ["ID", "ФИО", "Класс", "Кл. руководитель", "Достижения", "Дата создания"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")

        # Данные
        for row, student in enumerate(students, 2):
            ws.cell(row=row, column=1, value=student.id)
            ws.cell(row=row, column=2, value=student.full_name)
            ws.cell(row=row, column=3, value=student.class_name)
            ws.cell(row=row, column=4, value=student.class_teacher)
            ach_cell = ws.cell(row=row, column=5, value=student.achievements or "")
            # Включаем перенос текста внутри ячейки
            ach_cell.alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(row=row, column=6, value=student.created_at.strftime("%Y-%m-%d %H:%M") if student.created_at else "")

        # Автоподбор ширины колонок
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

        # Оставляем авто-высоту строк (по умолчанию), т.к. wrap_text=True на ячейке достижений

        # Сохраняем в память
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        # Возвращаем файл для скачивания
        filename = f"ученики_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    return app


# Создаем приложение
app = create_app()


if __name__ == "__main__":
    # Запускаем локальный сервер разработчика
    app.run(debug=True)


