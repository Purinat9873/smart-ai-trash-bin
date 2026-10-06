@echo off
title SMART AI TRASH BIN - LIVE SERVICE
echo ======================================================================
echo    SMART AI TRASH BIN - LIVE CONTINUOUS SERVICE
echo ======================================================================
echo  Port: COM6 (ESP32-S3) + OV2640 + OLED + Sensors + Servo (GPIO 21)
echo.
echo  AI Model: Loading Custom YOLOv8...
echo ======================================================================
echo.

python ai_training\smart_bin_service.py

echo.
echo Press any key to exit...
pause > nul
