from app import app, db, mebbis_json_yukle
from models import Basvuru
import glob
import os

def fix_detailed_statuses():
    # En son JSON dosyasını bul (mebbis_verileri_*.json)
    list_of_files = glob.glob('mebbis_verileri_*.json')
    if not list_of_files:
        print("JSON dosyası bulunamadı!")
        return
        
    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"Processing {latest_file}...")
    
    with app.app_context():
        # mebbis_json_yukle fonksiyonu zaten güncellendiği için 
        # sadece tekrar çalıştırmak kayıtları güncelleyecektir.
        # Ancak mevcut kayıtlar "Onay Bekliyor" -> "tamamlandi" olduğu için koruma mekanizmasına takılabilir.
        # Bu yüzden önce "tamamlandi" olanları (eğer Yönetici varsa) düzeltmek için özel bir script yazalım
        # ya da mebbis_json_yukle'yi çağırıp database'deki durumu geçici olarak resetleyebiliriz ama tehlikeli.
        
        # update logic handled inside mebbis_json_yukle now handles imports correctly.
        # But we need to FORCE update the statuses for existing records based on the JSON content
        
        import json
        with open(latest_file, "r", encoding="utf-8") as f:
            veriler = json.load(f)
            
        count = 0
        for kayit in veriler:
            tablo = kayit.get("tablo_verileri", {})
            basvuru_no = ""
            for v in tablo.values():
                if isinstance(v, str) and "MEB" in v and len(v) > 10:
                    basvuru_no = v
                    break
            
            if not basvuru_no: continue
            
            b = Basvuru.query.filter_by(basvuru_no=basvuru_no).first()
            if not b: continue
            
            # Kurum İşlemini Bul
            kurum_islem = ""
            for k, v in tablo.items():
                if "KURUMUN" in k.upper() and "SON" in k.upper():
                    kurum_islem = str(v).upper()
                    break
            
            print(f"Checking {basvuru_no}: {kurum_islem}")
            
            # Regex ile esnek eşleşme
            import re
            
            # Y.NET.C. -> YÖNETİCİ, YONETICI, YNETICI vb. yakalar
            is_yonetici = re.search(r"Y.NET.C.", kurum_islem, re.IGNORECASE)
            is_degerlendirici = re.search(r"DE.ERLEND.R.C.", kurum_islem, re.IGNORECASE)

            if is_yonetici:
                if b.degerlendirme_durumu != "yonetici_onayinda" and b.degerlendirme_durumu not in ["okul_secimi", "onaylandi", "reddedildi"]:
                    print(f"  -> Updating to 'yonetici_onayinda'")
                    b.degerlendirme_durumu = "yonetici_onayinda"
                    count += 1
            elif is_degerlendirici:
                 # Mevcut durum zaten 'tamamlandi' olmalı, eğer değilse düzelt
                 # Belki 'devam' kalmışsa 'tamamlandi' yapabiliriz
                 if b.degerlendirme_durumu == "devam":
                     print(f"  -> Updating from 'devam' to 'tamamlandi' (Degerlendirici)")
                     b.degerlendirme_durumu = "tamamlandi"
                     count += 1
            
        db.session.commit()
        print(f"\nUpdated {count} records to 'yonetici_onayinda'.")

if __name__ == "__main__":
    fix_detailed_statuses()
