@echo off
rem Build GestureBoard and its Windows installer in one step.
rem
rem   1. PyInstaller -> dist\GestureBoard\GestureBoard.exe
rem   2. Inno Setup  -> Output\GestureBoard_Setup_1.0.0.exe
rem
rem Needs: pip install -r requirements.txt, and Inno Setup 6.

setlocal
cd /d "%~dp0"

echo === Building GestureBoard (PyInstaller) ===
python -m PyInstaller GestureBoard.spec --noconfirm --clean
if errorlevel 1 (
    echo.
    echo PyInstaller build failed.
    exit /b 1
)

echo.
echo === Building the installer (Inno Setup) ===
set "ISCC="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC for %%I in (ISCC.exe) do if not "%%~$PATH:I"=="" set "ISCC=%%~$PATH:I"

if not defined ISCC (
    echo Inno Setup 6 was not found. Install it with:
    echo   winget install --id JRSoftware.InnoSetup -e --source winget
    exit /b 1
)

"%ISCC%" installer.iss
if errorlevel 1 (
    echo.
    echo Installer build failed.
    exit /b 1
)

echo.
echo Done: %CD%\Output\GestureBoard_Setup_1.0.0.exe
endlocal
