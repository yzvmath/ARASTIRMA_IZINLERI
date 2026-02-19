from app import app, db
from models import Basvuru

def fix_specifics():
    with app.app_context():
        # 1. MEB.TT.2026.046416.01 -> Yeni Kayıt -> Bekliyor
        b1 = Basvuru.query.filter_by(basvuru_no="MEB.TT.2026.046416.01").first()
        if b1:
            print(f"Fixing {b1.basvuru_no}: {b1.degerlendirme_durumu} -> bekliyor (Ön Kontrol Devam Ediyor)")
            b1.degerlendirme_durumu = "bekliyor"
            
        # 2. MEB.TT.2025.044260.02 -> Yönetici Onay Kararı -> Okul Seçimi
        b2 = Basvuru.query.filter_by(basvuru_no="MEB.TT.2025.044260.02").first()
        if b2:
            print(f"Fixing {b2.basvuru_no}: {b2.degerlendirme_durumu} -> okul_secimi")
            b2.degerlendirme_durumu = "okul_secimi"

        db.session.commit()
        print("Done.")

if __name__ == "__main__":
    fix_specifics()
