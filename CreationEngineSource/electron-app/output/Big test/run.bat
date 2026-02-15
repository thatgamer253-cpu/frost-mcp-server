@echo off
if not exist venv (
    python -m venv venv
)

call venv\Scripts\activate

if not exist requirements.txt (
    echo aiohttp> requirements.txt
    echo fastapi>> requirements.txt
    echo state_manager>> requirements.txt
    echo PyYAML>> requirements.txt
    echo pysqlite3>> requirements.txt
    echo task_manager>> requirements.txt
    echo asyncio>> requirements.txt
    echo error_handler>> requirements.txt
    echo plugin_loader>> requirements.txt
)

pip install -r requirements.txt

python app.py

pause