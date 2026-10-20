@echo off
rem Builds build\dist\Weather\Weather.exe (one folder). Run from anywhere: build\build.bat
rem Then: ..\..\.venv\Scripts\python build\make_zip.py  ->  "2. Output\Weather.zip" (+ update zip)
setlocal
cd /d "%~dp0.."
set PY=..\..\.venv\Scripts\python.exe

if not exist "%PY%" (
  echo Missing the project venv. Create it first ^(see SKILL.md^).
  exit /b 1
)

echo Building the panel guides from the cards...
"%PY%" tools\build_help.py || exit /b 1
if not exist build\icon.ico "%PY%" build\make_icon.py

echo Building...
"%PY%" -m PyInstaller --noconfirm --clean --distpath build\dist --workpath build\work build\weather.spec || exit /b 1

echo.
echo Done: build\dist\Weather\Weather.exe
endlocal
