@echo off
title Minecraft Launcher Guard

:: ==========================================
:: 1. GUARD: Check if playit.exe is running
:: ==========================================
tasklist /FI "IMAGENAME eq playit.exe" 2>NUL | find /I /N "playit.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [INFO] playit.gg is already running. Skipping launch...
) else (
    echo [LAUNCH] Starting playit.gg minimized...
    start /min "" "C:\\Program Files\\playit_gg\\bin\\playit.exe"
    :: Give the tunnel 3 seconds to spin up only if we launched it fresh
    timeout /t 3 /nobreak >nul
)

:: ==========================================
:: 2. GUARD: Check if Minecraft (Java) is running
:: ==========================================
tasklist /FI "IMAGENAME eq java.exe" 2>NUL | find /I /N "java.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [WARN] A Java process is already running! Skipping server launch to prevent corruption...
    timeout /t 3 >nul
    exit
) else (
    echo [LAUNCH] Starting Minecraft Server minimized...
    cd /d "C:\Users\arjun\Downloads\minecraft_server"
    start /min "" "run.bat"
)

:: Clean exit for the FastAPI subprocess engine
exit
