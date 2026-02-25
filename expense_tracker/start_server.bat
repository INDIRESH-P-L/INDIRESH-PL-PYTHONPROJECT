@echo off
TITLE Expense Tracker Server
echo ==============================================
echo   Starting Expense Tracker...
echo ==============================================

if not exist ".venv" (
    echo Creating virtual environment...
    "C:\Users\indir\AppData\Local\Programs\Python\Python314\python.exe" -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing requirements...
pip install -r requirements.txt --quiet

echo.
echo Server starting...
python run.py
pause
