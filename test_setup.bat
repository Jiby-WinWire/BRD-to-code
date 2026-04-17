@echo off
REM =====================================================
REM 🧪 BRD-to-Code Testing Suite (Windows)
REM Language Edition: Python + C#/.NET
REM =====================================================

setlocal enabledelayedexpansion

color 0A
cls

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║   🧪 BRD-to-Code Testing Suite (Windows)                   ║
echo ║   Language Edition: Python + C#/.NET                        ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM ==================== SYSTEM CHECKS ====================

echo [INFO] Checking system requirements...
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install from python.org
    pause
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] Python: !PYTHON_VERSION!
)

REM Check pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip not found!
    pause
    exit /b 1
) else (
    echo [OK] pip package manager found
)

REM Check .NET (optional)
dotnet --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] .NET SDK not found - C# generation won't run
) else (
    for /f "tokens=*" %%i in ('dotnet --version 2^>^&1') do set DOTNET_VERSION=%%i
    echo [OK] .NET: !DOTNET_VERSION!
)

echo.
echo [INFO] File structure validation...
echo.

REM Check key files
set files_ok=0
for %%F in (
    "app.py"
    "supervisor_language.py"
    "START_HERE.md"
    "QUICK_START.md"
) do (
    if exist "%%F" (
        echo [OK] %%F
        set /a files_ok=!files_ok!+1
    ) else (
        echo [MISSING] %%F
    )
)

echo.
echo [INFO] Sample applications validation...
echo.

if exist "output\python-sample\models.py" (
    echo [OK] Python sample: models.py
) else (
    echo [MISSING] Python sample
)

if exist "output\csharp-sample\Models\Todo.cs" (
    echo [OK] C# sample: Models/Todo.cs
) else (
    echo [MISSING] C# sample
)

REM ==================== PYTHON CODE CHECKS ====================

echo.
echo [INFO] Python syntax validation...
echo.

python -m py_compile app.py >nul 2>&1
if errorlevel 1 (
    echo [ERROR] app.py has syntax errors
) else (
    echo [OK] app.py syntax valid
)

python -m py_compile supervisor_language.py >nul 2>&1
if errorlevel 1 (
    echo [ERROR] supervisor_language.py has syntax errors
) else (
    echo [OK] supervisor_language.py syntax valid
)

REM ==================== IMPORT TESTS ====================

echo.
echo [INFO] Testing Python imports...
echo.

python -c "from app import LanguageSelector; print('[OK] LanguageSelector imported')" 2>nul || echo [ERROR] Failed to import LanguageSelector

python -c "from supervisor_language import SupervisorWithLanguage; print('[OK] SupervisorWithLanguage imported')" 2>nul || echo [ERROR] Failed to import SupervisorWithLanguage

REM ==================== TEST SUMMARY ====================

echo.
echo ════════════════════════════════════════════════════════════════
echo [OUTPUT] ✅ VALIDATION COMPLETE
echo ════════════════════════════════════════════════════════════════
echo.

echo 📋 NEXT STEPS:
echo.
echo 1. Start the application:
echo    python app.py
echo.
echo 2. Choose language:
echo    1 = Python (FastAPI)
echo    2 = C# (.NET Core)
echo.
echo 3. Enter your requirements (or press Enter for demo)
echo.
echo 4. Generated code will be in:
echo    output\[timestamp-folder]\
echo.
echo 5. Open RUN_INSTRUCTIONS.txt for detailed setup
echo.

echo 📚 MANUAL TESTING:
echo.
echo Python FastAPI Sample:
echo   cd output\python-sample
echo   pip install -r requirements.txt
echo   python run.py
echo   :: Open http://localhost:8000
echo.
echo C# .NET Core Sample:
echo   cd output\csharp-sample
echo   dotnet restore
echo   dotnet ef database update
echo   dotnet run
echo   :: Open https://localhost:7000
echo.

echo ════════════════════════════════════════════════════════════════
echo 🚀 Setup is complete! Ready to generate applications.
echo ════════════════════════════════════════════════════════════════
echo.

REM Optional: Open START_HERE.md
echo Would you like to open documentation?
echo 1. START_HERE.md (main guide)
echo 2. QUICK_START.md (quick reference)
echo 3. Run app.py directly
echo 0. Exit

set /p choice="Enter choice (0-3): "

if "!choice!"=="1" if exist "START_HERE.md" start notepad START_HERE.md
if "!choice!"=="2" if exist "QUICK_START.md" start notepad QUICK_START.md
if "!choice!"=="3" python app.py

pause
