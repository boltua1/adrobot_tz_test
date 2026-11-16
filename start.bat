@echo off
chcp 65001 >nul
title Keitaro Flow Manager - Server

echo ===================================================
echo   Запуск Keitaro Campaign Manager ^& Flow Editor
echo ===================================================

cd /d "%~dp0"

:: 1. Проверка .env
if not exist ".env" (
    echo [!] Файл .env не найден. Копирую из .env.example...
    copy .env.example .env >nul
    echo [!] Проверьте настройки в файле .env перед началом работы.
)

:: 2. Проверка виртуального окружения
if not exist "venv\Scripts\activate.bat" (
    echo [*] Создание виртуального окружения venv...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Не удалось создать виртуальное окружение. Убедитесь, что Python установлен.
        pause
        exit /b 1
    )
    echo [*] Установка зависимостей из requirements.txt...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

:: 3. Применение миграций БД
echo [*] Применение миграций базы данных (Alembic)...
alembic upgrade head
if errorlevel 1 (
    echo [ERROR] Ошибка применения миграций.
    pause
    exit /b 1
)

:: 4. Открытие браузера и запуск Uvicorn
echo [*] Сервер запускается на http://127.0.0.1:8000
echo [*] Для остановки нажмите CTRL+C в этом окне или запустите stop.bat
echo ===================================================

start "" "http://localhost:8000"
uvicorn app.main:app --reload --port 8000
