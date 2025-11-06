#!/bin/bash

# Установщик для Ubuntu Server
# Панель управления учениками ZCS-RP-010

set -e  # Остановка при ошибке

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

clear
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Установщик панели управления учениками${NC}"
echo -e "${GREEN}           ZCS-RP-010${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Проверка, что запущено на Ubuntu/Debian
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ "$ID" != "ubuntu" && "$ID" != "debian" ]]; then
        echo -e "${YELLOW}Предупреждение: Этот установщик предназначен для Ubuntu/Debian${NC}"
    fi
else
    echo -e "${YELLOW}Предупреждение: Не удалось определить ОС${NC}"
fi

# Проверка прав root (для установки системных пакетов)
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}Обнаружен запуск от root. Установка системных пакетов...${NC}"
    INSTALL_SYSTEM_PACKAGES=true
else
    INSTALL_SYSTEM_PACKAGES=false
    echo -e "${YELLOW}Запуск без root. Системные пакеты не будут установлены.${NC}"
fi

# Установка системных зависимостей (если есть root)
if [ "$INSTALL_SYSTEM_PACKAGES" = true ]; then
    echo -e "${YELLOW}[0/7]${NC} Обновление списка пакетов..."
    apt-get update -qq
    echo -e "${YELLOW}[0/7]${NC} Установка системных зависимостей..."
    apt-get install -y python3 python3-pip python3-venv > /dev/null 2>&1 || true
fi

# Проверка Python
echo -e "${YELLOW}[1/7]${NC} Проверка Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ОШИБКА: Python 3 не найден!${NC}"
    if [ "$INSTALL_SYSTEM_PACKAGES" = false ]; then
        echo "Установите Python 3: sudo apt-get install python3 python3-pip python3-venv"
    fi
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓${NC} $PYTHON_VERSION"

# Проверка pip
echo -e "${YELLOW}[2/7]${NC} Проверка pip..."
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}pip3 не найден, пытаемся установить...${NC}"
    python3 -m ensurepip --upgrade || {
        echo -e "${RED}ОШИБКА: Не удалось установить pip3!${NC}"
        if [ "$INSTALL_SYSTEM_PACKAGES" = false ]; then
            echo "Установите pip3: sudo apt-get install python3-pip"
        fi
        exit 1
    }
fi
echo -e "${GREEN}✓${NC} pip найден"

# Настройка конфигурации
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Настройка конфигурации${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Ввод пароля администратора
echo -e "${YELLOW}Настройка доступа администратора:${NC}"
read -p "Введите логин администратора [admin]: " ADMIN_USERNAME
ADMIN_USERNAME=${ADMIN_USERNAME:-admin}

while true; do
    read -sp "Введите пароль администратора: " ADMIN_PASSWORD
    echo ""
    if [ -z "$ADMIN_PASSWORD" ]; then
        echo -e "${RED}Пароль не может быть пустым!${NC}"
        continue
    fi
    read -sp "Подтвердите пароль: " ADMIN_PASSWORD_CONFIRM
    echo ""
    if [ "$ADMIN_PASSWORD" != "$ADMIN_PASSWORD_CONFIRM" ]; then
        echo -e "${RED}Пароли не совпадают! Попробуйте снова.${NC}"
    else
        break
    fi
done

# Генерация секретного ключа
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Настройки сервера
read -p "Порт для запуска приложения [5000]: " FLASK_PORT
FLASK_PORT=${FLASK_PORT:-5000}

read -p "Хост для запуска [0.0.0.0]: " FLASK_HOST
FLASK_HOST=${FLASK_HOST:-0.0.0.0}

# Создание .env файла
echo -e "${YELLOW}[3/7]${NC} Создание конфигурационного файла..."
cat > .env << EOF
# Конфигурация панели управления учениками ZCS-RP-010
# Создано автоматически при установке

ADMIN_USERNAME=$ADMIN_USERNAME
ADMIN_PASSWORD=$ADMIN_PASSWORD
FLASK_SECRET_KEY=$SECRET_KEY
FLASK_HOST=$FLASK_HOST
FLASK_PORT=$FLASK_PORT
FLASK_DEBUG=False
EOF

# Защита .env файла
chmod 600 .env 2>/dev/null || true
echo -e "${GREEN}✓${NC} Конфигурация сохранена в .env"

# Создание виртуального окружения
echo -e "${YELLOW}[4/7]${NC} Создание виртуального окружения..."
if [ -d ".venv" ]; then
    echo -e "${YELLOW}Виртуальное окружение уже существует, пересоздаем...${NC}"
    rm -rf .venv
fi

python3 -m venv .venv
if [ $? -ne 0 ]; then
    echo -e "${RED}ОШИБКА: Не удалось создать виртуальное окружение!${NC}"
    echo "Установите python3-venv: sudo apt-get install python3-venv"
    exit 1
fi
echo -e "${GREEN}✓${NC} Виртуальное окружение создано"

# Активация виртуального окружения
echo -e "${YELLOW}[5/7]${NC} Активация виртуального окружения..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}ОШИБКА: Не удалось активировать виртуальное окружение!${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Виртуальное окружение активировано"

# Установка зависимостей
echo -e "${YELLOW}[6/7]${NC} Установка зависимостей Python..."
pip install --upgrade pip --quiet
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}ОШИБКА: Не удалось установить зависимости!${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Зависимости установлены"

# Инициализация базы данных
echo -e "${YELLOW}[7/7]${NC} Инициализация базы данных..."
python3 -c "from database import init_db; init_db(); print('База данных инициализирована')" 2>/dev/null || {
    echo -e "${YELLOW}База данных уже существует или произошла ошибка${NC}"
}
echo -e "${GREEN}✓${NC} База данных готова"

# Обновление app.py для использования .env
echo ""
echo -e "${YELLOW}Настройка приложения...${NC}"
# Проверяем, нужно ли установить python-dotenv
if ! python3 -c "import dotenv" 2>/dev/null; then
    pip install python-dotenv --quiet
fi

# Обновляем app.py чтобы загружать .env
if ! grep -q "from dotenv import load_dotenv" app.py 2>/dev/null; then
    # Добавляем загрузку .env в начало app.py
    sed -i '1a from dotenv import load_dotenv\nload_dotenv()' app.py 2>/dev/null || {
        echo -e "${YELLOW}Не удалось автоматически обновить app.py${NC}"
        echo -e "${YELLOW}Добавьте в начало app.py:${NC}"
        echo "  from dotenv import load_dotenv"
        echo "  load_dotenv()"
    }
fi

# Обновляем чтение пароля из переменных окружения
if ! grep -q "ADMIN_PASSWORD = os.environ.get" app.py 2>/dev/null; then
    # Заменяем хардкод пароля на чтение из переменных окружения
    sed -i 's/passw = "12345"/passw = os.environ.get("ADMIN_PASSWORD", "12345")/' app.py 2>/dev/null || true
    sed -i 's/user = "admin"/user = os.environ.get("ADMIN_USERNAME", "admin")/' app.py 2>/dev/null || true
fi

echo -e "${GREEN}✓${NC} Приложение настроено"

# Настройка systemd service для автозапуска
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Настройка автозапуска (systemd)${NC}"
echo -e "${BLUE}========================================${NC}"
read -p "Настроить автозапуск приложения как системный сервис? (y/n) [y]: " SETUP_SERVICE
SETUP_SERVICE=${SETUP_SERVICE:-y}

if [[ "$SETUP_SERVICE" =~ ^[Yy]$ ]]; then
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}Для настройки systemd service нужны права root${NC}"
        echo -e "${YELLOW}Запустите: sudo ./install.sh${NC}"
        echo -e "${YELLOW}Или настройте сервис вручную позже${NC}"
    else
        # Определяем путь к проекту и пользователя
        PROJECT_DIR=$(pwd)
        SERVICE_USER=$(logname 2>/dev/null || echo "www-data")
        read -p "Пользователь для запуска сервиса [$SERVICE_USER]: " SERVICE_USER_INPUT
        SERVICE_USER=${SERVICE_USER_INPUT:-$SERVICE_USER}
        
        # Создаем systemd service файл
        SERVICE_FILE="/etc/systemd/system/zcs-rp-010.service"
        cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Панель управления учениками ZCS-RP-010
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/.venv/bin"
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/.venv/bin/python3 $PROJECT_DIR/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
        
        # Перезагружаем systemd и включаем сервис
        systemctl daemon-reload
        systemctl enable zcs-rp-010.service
        
        echo -e "${GREEN}✓${NC} Systemd service создан и включен"
        echo ""
        echo -e "${YELLOW}Управление сервисом:${NC}"
        echo -e "  ${GREEN}Запуск:${NC}   sudo systemctl start zcs-rp-010"
        echo -e "  ${GREEN}Остановка:${NC} sudo systemctl stop zcs-rp-010"
        echo -e "  ${GREEN}Статус:${NC}    sudo systemctl status zcs-rp-010"
        echo -e "  ${GREEN}Логи:${NC}      sudo journalctl -u zcs-rp-010 -f"
        echo ""
        
        # Запускаем сервис
        read -p "Запустить сервис сейчас? (y/n) [y]: " START_NOW
        START_NOW=${START_NOW:-y}
        if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
            systemctl start zcs-rp-010.service
            sleep 2
            if systemctl is-active --quiet zcs-rp-010.service; then
                echo -e "${GREEN}✓${NC} Сервис запущен и работает!"
            else
                echo -e "${RED}ОШИБКА: Сервис не запустился${NC}"
                echo -e "${YELLOW}Проверьте логи: sudo journalctl -u zcs-rp-010${NC}"
            fi
        fi
    fi
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Установка завершена успешно!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Информация о доступе:${NC}"
echo -e "  ${GREEN}Логин:${NC} $ADMIN_USERNAME"
echo -e "  ${GREEN}Пароль:${NC} [установлен при установке]"
echo ""
if systemctl is-active --quiet zcs-rp-010.service 2>/dev/null; then
    echo -e "${GREEN}✓ Сервис запущен и работает в фоне 24/7${NC}"
    echo ""
    echo -e "${YELLOW}Приложение доступно по адресу:${NC}"
    echo -e "  ${GREEN}http://$FLASK_HOST:$FLASK_PORT${NC}"
    echo ""
    echo -e "${YELLOW}Управление сервисом:${NC}"
    echo -e "  ${GREEN}sudo systemctl start zcs-rp-010${NC}   - запустить"
    echo -e "  ${GREEN}sudo systemctl stop zcs-rp-010${NC}    - остановить"
    echo -e "  ${GREEN}sudo systemctl status zcs-rp-010${NC}   - статус"
    echo -e "  ${GREEN}sudo journalctl -u zcs-rp-010 -f${NC}    - логи"
else
    echo -e "${YELLOW}Для запуска приложения:${NC}"
    echo -e "  ${GREEN}./run.sh${NC}  (ручной запуск)"
    echo ""
    echo -e "${YELLOW}Или настройте systemd service для автозапуска:${NC}"
    echo -e "  ${GREEN}sudo systemctl enable zcs-rp-010${NC}"
    echo ""
    echo -e "${YELLOW}Приложение будет доступно по адресу:${NC}"
    echo -e "  ${GREEN}http://$FLASK_HOST:$FLASK_PORT${NC}"
fi
echo ""
echo -e "${YELLOW}Для продакшн-использования рекомендуется:${NC}"
echo -e "  - Настроить nginx как reverse proxy"
echo -e "  - Настроить SSL сертификат (Let's Encrypt)"
echo ""
