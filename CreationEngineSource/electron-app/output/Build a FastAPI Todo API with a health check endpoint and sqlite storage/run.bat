@echo off

REM Check if virtual environment exists
IF NOT EXIST "venv" (
    python -m venv venv
)

REM Activate the virtual environment
CALL venv\Scripts\activate

REM Install dependencies
pip install -r requirements.txt

REM Run the application
python main.py

REM Pause to keep the window open
pause