@echo off
title SMART AI TRASH BIN - CLOUD AI SERVER
echo ======================================================================
echo    SMART AI TRASH BIN - PRODUCTION CLOUD AI SERVER
echo ======================================================================
echo  Model: Custom YOLOv8 (smart_bin_best.pt)
echo  Endpoint: POST /classify
echo.
echo  Starting server on port 5000...
echo ======================================================================
echo.

python ai_training\cloud_ai_server.py

echo.
echo Press any key to exit...
pause > nul
