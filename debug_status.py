from app import app, db
from models import Basvuru, BasvuruDegerlendirici

with app.app_context():
    basvurular = Basvuru.query.all()
    print(f"{'ID':<5} {'No':<20} {'Durum':<15} {'MEBBIS State':<25} {'Deg Sayisi':<10}")
    print("-" * 80)
    for b in basvurular:
        deg_sayisi = BasvuruDegerlendirici.query.filter_by(basvuru_id=b.id).count()
        print(f"{b.id:<5} {b.basvuru_no:<20} {str(b.degerlendirme_durumu):<15} {str(b.basvuru_durumu):<25} {deg_sayisi:<10}")
