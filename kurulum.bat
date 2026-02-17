@echo off
chcp 65001 >nul
echo ══════════════════════════════════════════════════════
echo   MEB Araştırma İzni - Kurulum
echo ══════════════════════════════════════════════════════
echo.
echo [1/2] Python paketleri kuruluyor...
pip install -r requirements.txt
echo.
echo [2/2] Veritabanı oluşturuluyor...
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('   Veritabanı hazır.')"
echo.
echo ══════════════════════════════════════════════════════
echo   ✅ Kurulum tamamlandı!
echo   Başlatmak için: baslat.bat
echo ══════════════════════════════════════════════════════
pause
