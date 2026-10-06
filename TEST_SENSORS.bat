@echo off
chcp 65001 >nul
title ทดสอบเซนเซอร์และจอ OLED (ESP32-S3)
echo ========================================================
echo   [HARDWARE TEST 2] คอมไพล์และอัปโหลดโค้ดทดสอบ IR, Ultrasonic, OLED
echo ========================================================
echo บอร์ด: ESP32-S3 Dev Module
echo พอร์ต: COM6
echo.

arduino-cli compile -b esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=16M,PSRAM=opi -u -p COM6 "%~dp0tests\hardware_tests\02_sensors_test\02_sensors_test.ino"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   [SUCCESS] อัปโหลดสำเร็จ! ท่านสามารถเปิด Serial Monitor เพื่อดูค่าเซนเซอร์แบบ Real-time ได้
    echo ========================================================
) else (
    echo.
    echo   [ERROR] เกิดข้อผิดพลาดในการอัปโหลด
)

echo.
pause
