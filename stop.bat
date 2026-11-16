@echo off
chcp 65001 >nul
title Остановка Keitaro Flow Manager

echo ===================================================
echo   Остановка сервера Keitaro Flow Manager (порт 8000)
echo ===================================================

set "FOUND=0"
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo [*] Завершение процесса с PID %%a...
    taskkill /F /PID %%a >nul 2>&1
    set "FOUND=1"
)

if "%FOUND%"=="1" (
    echo [OK] Сервер на порту 8000 успешно остановлен.
) else (
    echo [INFO] Активных процессов на порту 8000 не обнаружено.
)

echo ===================================================
timeout /t 3 >nul
