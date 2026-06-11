@echo off
title System Shutdown Guard

echo [SHUTDOWN] Closing Minecraft Server gracefully...
:: taskkill /IM sends a friendly close signal (like clicking the X button)
taskkill /FI "IMAGENAME eq java.exe"

echo [SHUTDOWN] Closing playit.gg tunnel...
taskkill /F /IM playit.exe

exit
