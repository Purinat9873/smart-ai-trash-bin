@echo off
chcp 65001 >nul
title แฟลชโค้ด Smart Bin Demo (ESP32-S3)
echo ========================================================
echo   [UPLOAD DEMO] แฟลชโค้ดตอบรับ AI ลง ESP32-S3
echo ========================================================
echo * หากเปิด Serial Monitor ใน Arduino IDE อยู่ ให้ปิดแถบก่อน *
echo.
arduino-cli compile -b esp32:esp32:esp32s3:CDCOnBoot=default,FlashSize=16M,PSRAM=opi -u -p COM6 "%~dp0src\smart_trash_bin_demo\smart_trash_bin_demo.ino"
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   [SUCCESS] แฟลชโค้ดสำเร็จเรียบร้อย! พร้อมใช้งานร่วมกับ AI
    echo ========================================================
) else (
    echo.
    echo   [ERROR] แฟลชไม่สำเร็จ กรุณาเช็กว่าปิด Serial Monitor ใน Arduino IDE หรือยัง
)
echo.
pause
