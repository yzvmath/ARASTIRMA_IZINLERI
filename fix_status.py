# -*- coding: utf-8 -*-
from app import app, db, Basvuru, KriterDegerlendirme

def fix_statuses():
    with app.app_context():
        # 'devam' olan başvuruları bul
        basvurular = Basvuru.query.filter_by(degerlendirme_durumu='devam').all()
        fixed_count = 0
        
        for b in basvurular:
            # Eğer kriter değerlendirmelerinden hiçbiri doldurulmamışsa 'bekliyor'a geri al
            kriterler = KriterDegerlendirme.query.filter_by(basvuru_id=b.id).all()
            dolu_sayisi = sum(1 for k in kriterler if k.sonuc)
            
            if dolu_sayisi == 0:
                print(f"Fixing {b.basvuru_no}: devam -> bekliyor")
                b.degerlendirme_durumu = 'bekliyor'
                fixed_count += 1
        
        db.session.commit()
        print(f"\nToplam {fixed_count} başvuru 'bekliyor' durumuna geri döndürüldü.")

if __name__ == "__main__":
    fix_statuses()
