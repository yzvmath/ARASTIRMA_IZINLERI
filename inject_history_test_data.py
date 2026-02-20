from app import app, db
from models import Basvuru
from datetime import datetime

with app.app_context():
    try:
        # Eski test verilerini temizle
        Basvuru.query.filter(Basvuru.basvuru_no.in_(['2024.TEST.01', '2024.TEST.02'])).delete(synchronize_session=False)
        db.session.commit()
        
        # 01 record (Tamamlananlar / Arşiv)
        b1 = Basvuru(
            basvuru_no='2024.TEST.01',
            basvuru_tarihi='01.01.2024',
            ad_soyad='Test Kullanıcı (Ahmet)',
            arastirma_adi='Eğitim Araştırmaları (İlk Başvuru)',
            arastirma_niteligi='Yüksek Lisans Tezi',
            degerlendirme_durumu='reddedildi',
            koordinator_karari='RED',
            koordinator_notu='Metodoloji eksik.',
            il_sayisi='1',
            okul_kurum_sayisi='5',
            meslek='Öğretmen',
            calistigi_kurum='Deneme Okulu'
        )
        
        # 02 record (Ana Sayfa / Başvurular)
        b2 = Basvuru(
            basvuru_no='2024.TEST.02',
            basvuru_tarihi='15.02.2024',
            ad_soyad='Test Kullanıcı (Ahmet)',
            arastirma_adi='Eğitim Araştırmaları (Revize Edilmiş Başvuru)',
            arastirma_niteligi='Yüksek Lisans Tezi',
            degerlendirme_durumu='bekliyor',
            koordinator_karari=None,
            il_sayisi='1',
            okul_kurum_sayisi='5',
            meslek='Öğretmen',
            calistigi_kurum='Deneme Okulu'
        )
        
        db.session.add(b1)
        db.session.add(b2)
        db.session.commit()
        print("Test verileri başarıyla eklendi!")
        print("- 2024.TEST.01 (Arşiv - Reddedildi)")
        print("- 2024.TEST.02 (Ana Sayfa - Bekliyor)")
    except Exception as e:
        print(f"Veriler eklenirken hata oluştu: {e}")
        db.session.rollback()
