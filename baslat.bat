@echo off
chcp 65001 >nul
echo ══════════════════════════════════════════════════════
echo   MEB Araştırma İzni - Değerlendirme Platformu
echo ══════════════════════════════════════════════════════
echo.
echo   Sunucu başlatılıyor...
echo   Adres: http://127.0.0.1:5000
echo.
echo   Durdurmak için: bitir.bat veya Ctrl+C
echo ══════════════════════════════════════════════════════
echo.
start http://127.0.0.1:5000
python app.py
