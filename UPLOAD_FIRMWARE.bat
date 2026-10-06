@echo off
chcp 65001 >nul
title อัปโหลดเฟิร์มแวร์ถังขยะอัจฉริยะ (ESP32-S3 N16R8)
echo ========================================================
echo   [SMART TRASH BIN] เริ่มต้นคอมไพล์และอัปโหลดเฟิร์มแวร์
echo ========================================================
echo บอร์ด: ESP32-S3 Dev Module (16MB Flash, 8MB Octal PSRAM)
echo พอร์ต: COM6
echo.

arduino-cli compile -b esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=16M,PSRAM=opi,PartitionScheme=app3M_fat9M_16MB -u -p COM6 "%~dp0src\smart_trash_bin\smart_trash_bin.ino"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   [SUCCESS] อัปโหลดเฟิร์มแวร์สำเร็จเรียบร้อย!
    echo ========================================================
) else (
    echo.
    echo ========================================================
    echo   [ERROR] เกิดข้อผิดพลาดในการอัปโหลด กรุณาตรวจสอบสาย USB หรือกดปุ่ม BOOT บนบอร์ดค้างไว้ขณะเริ่ม Flash
    echo ========================================================
)

echo.
pause
