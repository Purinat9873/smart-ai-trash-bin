@echo off
chcp 65001 >nul
title ทดสอบฮาร์ดแวร์ Servo + IR + Ultrasonic อย่างละ 1 ตัว
echo ===================================================================
echo   🧪 HARDWARE TEST: ทดสอบ Servo (21), IR (0), Ultrasonic (14/47)
echo ===================================================================
echo กำลังแฟลชโค้ดทดสอบลงบอร์ด ESP32-S3...
echo.

arduino-cli compile -b esp32:esp32:esp32s3:CDCOnBoot=default,FlashSize=16M,PSRAM=opi -u -p COM6 "%~dp0tests\hardware_tests\05_single_component_test\05_single_component_test.ino"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   [SUCCESS] แฟลชโค้ดสำเร็จ! หน้าจอ OLED จะเริ่มแสดงค่าสดๆ ทันที
    echo   -> ลองเอามือเลื่อนเข้า-ออกหน้า Ultrasonic ดูตัวเลข cm
    echo   -> ลองเอามือบังเซนเซอร์ IR ดูเซอร์โวหมุน 90 องศา
    echo ========================================================
    echo.
    timeout /t 2 >nul
    arduino-cli monitor -p COM6 -c baudrate=115200
) else (
    echo.
    echo   [ERROR] เกิดข้อผิดพลาดในการอัปโหลด กรุณาตรวจสอบว่าปิด Serial Monitor หรือยัง
    pause
)
