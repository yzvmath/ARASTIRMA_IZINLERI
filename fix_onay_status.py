from app import app, db
from models import Basvuru

def fix_database():
    with app.app_context():
        # 'devam' veya 'bekliyor' olup MEBBIS durumu 'ONAY' içerenleri bul
        basvurular = Basvuru.query.filter(
            Basvuru.degerlendirme_durumu.in_(['devam', 'bekliyor']),
            Basvuru.basvuru_durumu.ilike('%ONAY%')
        ).all()
        
        fixed_count = 0
        for b in basvurular:
            print(f"Fixing {b.basvuru_no}: {b.degerlendirme_durumu} -> tamamlandi")
            b.degerlendirme_durumu = 'tamamlandi'
            fixed_count += 1
            
        db.session.commit()
        print(f"\nTotal records fixed: {fixed_count}")

if __name__ == "__main__":
    fix_database()
