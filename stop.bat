@echo off
rem Tat backend, Streamlit, frontend. Them -Docker de dung ca PostgreSQL + Qdrant (khong xoa du lieu).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop.ps1" %*
pause
