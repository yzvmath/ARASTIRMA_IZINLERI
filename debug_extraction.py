import json
from app import _normalize_key

def test_extraction():
    with open('mebbis_verileri_20260218_130947.json', 'r', encoding='utf-8') as f:
        veriler = json.load(f)
    
    # Melike Atmaca'yı bul
    kayit = None
    for k in veriler:
        ad_soyad = k.get("detay_verileri", {}).get("Ad Soyad") or k.get("tablo_verileri", {}).get("AD SOYAD")
        if ad_soyad and "MELİKE" in ad_soyad.upper():
            kayit = k
            break
    
    if not kayit:
        print("Kayıt bulunamadı.")
        return
        
    detay = kayit.get("detay_verileri", {})
    
    tum_belgeler = []
    gordugum_urller = set()

    def _belgeleri_topla(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict) and "url" in item and "text" in item:
                            url = item["url"].strip()
                            text = item["text"].strip()
                            
                            clean_text = text
                            separator = None
                            if " - " in text: separator = " - "
                            elif " – " in text: separator = " – "
                            if separator:
                                parts = text.split(separator, 1)
                                if len(parts) > 1: clean_text = parts[1].strip()
                            
                            if not clean_text: clean_text = text
                            
                            base_text = clean_text
                            for ext in [".pdf", ".PDF", ".docx", ".DOCX", ".doc", ".DOC", ".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"]:
                                if base_text.endswith(ext):
                                    base_text = base_text[:-len(ext)].strip()
                                    break
                            
                            id_text = _normalize_key(base_text)
                            if id_text in ["ANA BASVURU", "ANA BAŞVURU", "BASVURU FORMU"]: continue

                            item["clean_text"] = base_text
                            id_url = url.replace("http://", "").replace("https://", "").replace("\\", "/").rstrip("/")

                            if id_url not in gordugum_urller and id_text not in gordugum_urller:
                                gordugum_urller.add(id_url)
                                gordugum_urller.add(id_text) 
                                tum_belgeler.append(item)
                elif isinstance(v, dict):
                    _belgeleri_topla(v)

    _belgeleri_topla(detay)
    
    print(f"Toplam Belge Sayısı: {len(tum_belgeler)}")
    for i, b in enumerate(tum_belgeler):
        print(f"{i+1}. {b['text']} -> {b['clean_text']}")

    kelimeler = {
        "belge_arastirma_proje": ["ARASTIRMA PROJE", "PROJE BILGILERI", "TEZ ONERISI"],
        "belge_veri_toplama": ["VERI TOPLAMA", "OLCEK", "ANKET", "MULAKAT"],
        "belge_taahhutname": ["TAAHHUTNAME"],
        "belge_etik_kurul": ["ETIK KURUL", "ONAY BELGESI"],
        "belge_gonullu_katilim": ["GONULLU KATILIM", "BILGILENDIRME"],
        "belge_veli_onam": ["VELI ONAM", "VELI IZIN"],
        "belge_olcek_izni": ["OLCEK KULLANIM", "IZIN", "ALANYAZIN"],
        "belge_enstitu_karari": ["ENSTITU", "YONETIM KURULU", "KARAR"]
    }
    
    dagitim = {k: [] for k in kelimeler.keys()}
    dagitim["diger_ekler"] = []
    
    for belge in tum_belgeler:
        txt_norm = _normalize_key(belge["text"])
        esanlesti = False
        for db_field, keys in kelimeler.items():
            if any(k in txt_norm for k in keys):
                dagitim[db_field].append(belge)
                esanlesti = True
                break
        if not esanlesti:
            dagitim["diger_ekler"].append(belge)
            
    print("\n--- DAGITIM ---")
    for k, v in dagitim.items():
        if v:
            print(f"{k}: {[b['clean_text'] for b in v]}")

if __name__ == "__main__":
    test_extraction()
