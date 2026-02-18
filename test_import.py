import os
import sys
from app import app, db, mebbis_json_yukle, Basvuru

# Setup context
ctx = app.app_context()
ctx.push()

# Path to the JSON file
json_path = r"d:\ARASTIMA_IZINLERI\mebbis_verileri_20260218_114323.json"

print(f"Testing import with {json_path}")

try:
    # Clear existing data for testing purposes
    # Order matters due to foreign keys if cascade is not set
    from models import KriterDegerlendirme, OnKontrol
    db.session.query(KriterDegerlendirme).delete()
    db.session.query(OnKontrol).delete()
    db.session.query(Basvuru).delete()
    db.session.commit()
    
    eklenen, atlanan, guncellenen = mebbis_json_yukle(json_path)
    
    print(f"Import Result: Added={eklenen}, Skipped={atlanan}, Updated={guncellenen}")
    
    if eklenen > 0 or guncellenen > 0:
        print("SUCCESS: Data imported successfully.")
        
        print("-" * 30)
        # Verify the specific problematic record
        target_no = "MEB.TT.2025.044260.02"
        b_target = Basvuru.query.filter_by(basvuru_no=target_no).first()
        if b_target:
            print(f"Sample Record: {b_target.basvuru_no}")
            print(f"  Ad Soyad: {b_target.ad_soyad}")
            print(f"  Telefon: {b_target.telefon}")
            print(f"  MEBBIS Durum: {b_target.basvuru_durumu}")
            print(f"  App Durum: {b_target.degerlendirme_durumu}")
            print("-" * 20)
        else:
            print(f"TARGET RECORD ({target_no}) NOT FOUND.")
            
        print("-" * 30)
        print("Checking all records for Phone/Name stats:")
        all_recs = Basvuru.query.all()
        for b in all_recs:
             if not b.ad_soyad or not b.telefon:
                 print(f"  {b.basvuru_no} -> Name: '{b.ad_soyad}', Phone: '{b.telefon}'")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    ctx.pop()
