@echo off
chcp 65001 >nul
echo ══════════════════════════════════════════════════════
echo   MEB Araştırma İzni - Sunucu Durdurma
echo ══════════════════════════════════════════════════════
echo.
echo   Flask sunucusu durduruluyor...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *app.py*" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo.
echo   ✅ Sunucu durduruldu.
echo ══════════════════════════════════════════════════════
timeout /t 3
