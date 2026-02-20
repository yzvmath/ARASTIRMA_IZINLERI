import json
import os
import glob
from app import app, db, Basvuru

def get_corrected_duration(kayit):
    """MEBBIS detay verisinden doğru uygulama süresini ayıklar."""
    detay = kayit.get("detay_verileri", {})
    uyg_tablo = detay.get("Uygulama Bilgileri", [])
    durations = []
    
    # 1. Tabloyu tara
    if uyg_tablo and isinstance(uyg_tablo, list):
        for row in uyg_tablo:
            if isinstance(row, list) and len(row) >= 6:
                duration = str(row[5]).strip()
                # Case-insensitive ve geniş kapsamlı eşleştirme
                match_keywords = ["ders", "saat", "dakika", " dk", "oturum"]
                if duration and duration not in durations and any(k in duration.lower() for k in match_keywords):
                    durations.append(duration)
    
    if durations:
        return ", ".join(durations)
    
    # 2. Fallback (Sadece Ders/Dakika/Saat içeriyorsa tablo dışı alanlara güven)
    # MEBBIS bazen "Uygulama Süresi" anahtarında direkt veriyi tutabilir
    kayit_data = kayit.get("kayit", {})
    val = kayit_data.get("Uygulama Süresi", "") or kayit_data.get("SÜRE", "")
    if any(k in str(val) for k in ["Ders", "Dakika", "Saat"]):
        return str(val).strip()
        
    return None

def fix_durations():
    with app.app_context():
        # Tüm JSON dosyalarını bul (en yeni olan en son işlenecek şekilde sıralı kabul edelim)
        json_files = glob.glob("mebbis_verileri_*.json")
        if not json_files:
            print("Hata: mebbis_verileri_*.json dosyası bulunamadı.")
            return

        print(f"{len(json_files)} adet JSON dosyası bulundu.")
        
        updated_count = 0
        
        for json_path in json_files:
            print(f"İşleniyor: {json_path}")
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for item in data:
                    tablo = item.get("tablo_verileri", {})
                    detay = item.get("detay_verileri", {})
                    
                    basvuru_no = detay.get("Başvuru Numarası") or tablo.get("BAŞVURU NO")
                    
                    if not basvuru_no:
                        continue
                    
                    basvuru = Basvuru.query.filter_by(basvuru_no=basvuru_no).first()
                    if basvuru:
                        new_duration = get_corrected_duration(item)
                        if new_duration:
                            old_val = basvuru.uygulama_suresi or ""
                            
                            if any(k in new_duration.lower() for k in ["ders", "dakika", "saat", "dk", "oturum"]) and \
                               ("gün" in old_val.lower() or "2026" in old_val or not old_val or "ders" not in old_val.lower()):
                                print(f"Güncelleniyor [{basvuru_no}]: {old_val} -> {new_duration}")
                                basvuru.uygulama_suresi = new_duration
                                updated_count += 1
                        else:
                            # Eğer yeni süre bulunamadıysa ama veritabanındaki değer "gün" veya "2026" (değerlendirme süresi) içeriyorsa, temizle
                            old_val = basvuru.uygulama_suresi or ""
                            if old_val and ("gün" in old_val.lower() or "2026" in old_val):
                                print(f"Yanlış süre temizleniyor [{basvuru_no}]: {old_val} -> ''")
                                basvuru.uygulama_suresi = ""
                                updated_count += 1
                            else:
                                # print(f"Süre bulunamadı [{basvuru_no}]")
                                pass
            except Exception as e:
                print(f"Hata [{json_path}]: {e}")

        db.session.commit()
        print(f"\nİşlem tamamlandı. Toplam {updated_count} kayıt güncellendi.")

if __name__ == "__main__":
    fix_durations()
