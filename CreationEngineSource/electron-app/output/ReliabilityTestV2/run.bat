@echo off
if not exist "venv" (
    python -m venv venv
)

call venv\Scripts\activate

pip install -r requirements.txt

python3 main.py

pause