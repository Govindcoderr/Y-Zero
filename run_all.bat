@echo off
REM run_all.bat - Start Workflow Builder on Windows

echo.
echo ============================================================
echo   Workflow Builder - FastAPI + Streamlit
echo ============================================================
echo.

REM Check Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if requirements are installed
python -c "import fastapi, streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required packages...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Error: Failed to install requirements
        pause
        exit /b 1
    )
)

echo Starting servers...
echo.
echo Starting FastAPI on http://localhost:8000
start /b python main.py

REM Wait for API to start
timeout /t 3 /nobreak

echo Starting Streamlit on http://localhost:8501
echo.
start http://localhost:8501
python -m streamlit run streamlit_app.py

pause
