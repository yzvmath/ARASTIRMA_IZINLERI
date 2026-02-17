@echo off
chcp 65001 >nul
echo ══════════════════════════════════════════════════════
echo   MEBBİS VERİ ÇEK - Araştırma İzinleri
echo ══════════════════════════════════════════════════════
echo.
echo   MEBBİS sisteminden veri çekme işlemi başlatılıyor...
echo   Tarayıcı açılacak, lütfen giriş yapınız.
echo.
echo ══════════════════════════════════════════════════════
echo.
python mebbis_veri_cek.py
echo.
if %ERRORLEVEL% EQU 0 (
    echo ══════════════════════════════════════════════════════
    echo   ✅ Veri çekme işlemi tamamlandı!
    echo ══════════════════════════════════════════════════════
) else (
    echo ══════════════════════════════════════════════════════
    echo   ❌ Hata oluştu! Lütfen hata mesajını kontrol edin.
    echo ══════════════════════════════════════════════════════
)
echo.
pause
