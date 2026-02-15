@echo off
if not exist .\venv (
    mkdir .\venv
    python -m venv .\venv
)
call .\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
pause