@echo off
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate
if exist requirements.txt (
    pip install -r requirements.txt
)
python main.py
pause