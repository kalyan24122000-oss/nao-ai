@echo off
echo ====================================
echo    AI Chatbot Admin Panel
echo    Building .exe file...
echo ====================================
echo.

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Install requests for better API handling
pip install requests

echo.
echo Building admin_panel.exe...
echo.

pyinstaller --onefile --windowed --name "AI_Chatbot_Admin" --icon=NONE admin_panel.py

echo.
echo ====================================
echo Build complete!
echo Your .exe file is in the "dist" folder
echo ====================================
pause
