from app import app, db, ON_KONTROL_MADDELERI
from models import Basvuru, OnKontrol

def debug_app_details():
    with app.app_context():
        basvuru_no = "MEB.TT.2026.046416.01"
        b = Basvuru.query.filter_by(basvuru_no=basvuru_no).first()
        
        if not b:
            print(f"Application {basvuru_no} not found!")
            return

        print(f"=== Application: {b.basvuru_no} (ID: {b.id}) ===")
        print(f"Status (DB): {b.degerlendirme_durumu}")
        print(f"Evaluators: {b.degerlendiriciler}")
        print(f"Teskilat Turu (DB): '{b.teskilat_turu}'")
        print(f"MEB Teskilati (DB): '{b.meb_teskilati}'")
        
        # Check OnKontrol items
        items = OnKontrol.query.filter_by(basvuru_id=b.id).all()
        valid_items = [i for i in items if i.durum] # Non-empty status
        
        print(f"\nTotal OnKontrol Items in DB: {len(items)}")
        print(f"Items with Status (Counted as Done): {len(valid_items)}")
        print(f"Required Items: {len(ON_KONTROL_MADDELERI)}")
        
        for item in items:
            print(f"  - Item {item.sira}: {item.durum} ({item.madde_adi[:30]}...)")
            
        # Check raw data for Institution Type
        import json
        try:
            raw_data = json.loads(b.veri_json) if b.veri_json else {}
            tablo = raw_data.get("tablo_verileri", {})
            detay = raw_data.get("detay_verileri", {})
            
            print(f"\n--- Raw Data Inspection ---")
            print(f"Uygulama Suresi (DB): '{b.uygulama_suresi}'")
            print("Tablo Keys containing 'SURE' or 'SÜRE':")
            
            for k, v in tablo.items():
                if "SURE" in k.upper() or "SÜRE" in k.upper():
                    print(f"  MATCH: '{k}': '{v}'")
                    
            for k, v in detay.items():
                if "KURUM" in k.upper() and "TURU" in k.upper():
                    print(f"Detay Key Match: '{k}' -> '{v}'")
                    
        except Exception as e:
            print(f"Error parsing JSON: {e}")

if __name__ == "__main__":
    debug_app_details()
