@echo off
cd /d "C:\Users\thatg\Desktop\Frost"
echo Starting Project Frost Dashboard...
start /b python -m streamlit run dashboard.py --server.port 8506 --server.headless true
echo Starting Autonomous Swarm Orchestrator...
start /b python swarm_runner.py
echo Waiting for dashboard to initialize...
timeout /t 5 >nul
start http://localhost:8506
exit
