#!/bin/bash

# Скрипт запуска приложения для Ubuntu Server

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Запуск панели управления учениками ZCS-RP-010...${NC}"

# Проверка виртуального окружения
if [ ! -d ".venv" ]; then
    echo -e "${RED}Виртуальное окружение не найдено!${NC}"
    echo "Запустите сначала: ./install.sh"
    exit 1
fi

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Файл .env не найден!${NC}"
    if [ -f ".env.example" ]; then
        read -p "Создать .env из примера? (y/n) [y]: " CREATE_ENV
        CREATE_ENV=${CREATE_ENV:-y}
        if [[ "$CREATE_ENV" =~ ^[Yy]$ ]]; then
            cp .env.example .env
            chmod 600 .env 2>/dev/null || true
            echo -e "${GREEN}✓${NC} Файл .env создан из .env.example"
            echo -e "${YELLOW}ВАЖНО: Отредактируйте .env и установите безопасный пароль администратора!${NC}"
            echo ""
        else
            echo "Запустите установщик: ./install.sh"
            exit 1
        fi
    else
        echo "Запустите установщик: ./install.sh"
        exit 1
    fi
fi

# Загрузка переменных окружения
source .env 2>/dev/null || true

# Активация виртуального окружения
source .venv/bin/activate

# Определение хоста и порта
HOST=${FLASK_HOST:-0.0.0.0}
PORT=${FLASK_PORT:-5000}

# Запуск приложения
echo -e "${GREEN}Приложение запущено!${NC}"
echo -e "${YELLOW}Адрес: http://${HOST}:${PORT}${NC}"
echo -e "${YELLOW}Для остановки нажмите Ctrl+C${NC}"
echo ""

python3 app.py

