@echo off
REM Launch the OcuLens-AI demo portal. Double-click this file, then open the Local URL it prints.
cd /d "%~dp0"
python -m streamlit run portal\app.py
pause
