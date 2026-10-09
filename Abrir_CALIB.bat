@echo off
setlocal
cd /d "%~dp0"
title Sistema CALIB

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m streamlit run main.py
    goto fim
)

if exist ".venv\.venv\Scripts\python.exe" (
    ".venv\.venv\Scripts\python.exe" -m streamlit run main.py
    goto fim
)

echo Nao encontrei o Python do ambiente virtual do CALIB.
echo Abra o terminal na pasta do projeto e confira se a pasta .venv existe.
pause
:fim
endlocal
