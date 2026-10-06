@echo off
chcp 65001 >nul
title เปิด Serial Monitor (COM6 @ 115200)
echo ========================================================
echo   เปิด Serial Monitor พอร์ต COM6 (Baudrate: 115200)
echo   กด Ctrl+C เพื่อออก
echo ========================================================
arduino-cli monitor -p COM6 -c baudrate=115200
pause
