#!/bin/bash

# Скрипт для создания .env файла из примера

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ -f ".env" ]; then
    echo -e "${YELLOW}Файл .env уже существует!${NC}"
    read -p "Перезаписать? (y/n) [n]: " OVERWRITE
    OVERWRITE=${OVERWRITE:-n}
    if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
        echo "Отменено."
        exit 0
    fi
fi

if [ ! -f ".env.example" ]; then
    echo -e "${RED}ОШИБКА: Файл .env.example не найден!${NC}"
    exit 1
fi

# Копируем пример
cp .env.example .env

# Генерируем секретный ключ
if command -v python3 &> /dev/null; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null)
    if [ -n "$SECRET_KEY" ]; then
        # Заменяем секретный ключ в .env
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/FLASK_SECRET_KEY=.*/FLASK_SECRET_KEY=$SECRET_KEY/" .env
        else
            # Linux
            sed -i "s/FLASK_SECRET_KEY=.*/FLASK_SECRET_KEY=$SECRET_KEY/" .env
        fi
    fi
fi

# Устанавливаем права доступа
chmod 600 .env 2>/dev/null || true

echo -e "${GREEN}✓${NC} Файл .env создан из .env.example"
echo ""
echo -e "${YELLOW}ВАЖНО: Отредактируйте .env и установите:${NC}"
echo -e "  - Безопасный пароль администратора (ADMIN_PASSWORD)"
echo -e "  - При необходимости измените другие настройки"
echo ""
echo -e "${YELLOW}Для редактирования:${NC}"
echo -e "  nano .env"
echo ""

