#!/usr/bin/env bash
echo ""
echo "  ============================================"
echo "   Инструменты полевой лингвистики"
echo "   Fieldwork Linguistics Tools"
echo "  ============================================"
echo ""

if ! command -v python3 &> /dev/null; then
    echo "  [!] Python не найден. Установите Python 3.11+"
    echo "      https://www.python.org/downloads/"
    exit 1
fi

cd "$(dirname "$0")"

echo "  Проверяем зависимости..."
pip3 install -q -r requirements.txt 2>/dev/null

echo ""
echo "  Запускаем сервер..."
echo "  Откройте в браузере: http://localhost:8000"
echo ""
echo "  Для остановки нажмите Ctrl+C"
echo ""

python3 -X utf8 -m uvicorn web.app:app --host 127.0.0.1 --port 8000 --reload
