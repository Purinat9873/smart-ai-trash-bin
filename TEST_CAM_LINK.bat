@echo off
chcp 65001 >nul
title ตรวจสอบการเชื่อมต่อ ESP32-CAM กับ ESP32-S3
echo ========================================================
echo   [CHECK LINK] อัปโหลดโค้ดทดสอบเช็กสัญญาณ ESP32-CAM
echo ========================================================
echo กำลังแฟลชโค้ดลง ESP32-S3 (COM6)...
echo.

arduino-cli compile -b esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=16M,PSRAM=opi -u -p COM6 "%~dp0tests\hardware_tests\03_cam_bridge_test\03_cam_bridge_test.ino"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   [SUCCESS] แฟลชโค้ดสำเร็จ! กำลังเปิดหน้าต่างมอนิเตอร์...
    echo   -> ให้ลองกดปุ่ม [RST] สีดำเล็กๆ บน ESP32-CAM 1 ครั้ง
    echo ========================================================
    echo.
    timeout /t 2 >nul
    arduino-cli monitor -p COM6 -c baudrate=115200
) else (
    echo.
    echo   [ERROR] เกิดข้อผิดพลาดในการอัปโหลด
    pause
)
