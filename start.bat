@echo off
rem Bam dup de khoi dong: Docker (PostgreSQL + Qdrant), backend, frontend React. Tham so: -Streamlit -Fake -NoFrontend -NoBrowser
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1" %*
if errorlevel 1 pause
