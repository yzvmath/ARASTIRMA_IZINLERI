from app import app, db, KRITERLER
from models import Basvuru, KriterDegerlendirme

def debug_app_status():
    with app.app_context():
        b = Basvuru.query.filter_by(basvuru_no="MEB.TT.2026.046207.02").first()
        if not b:
            print("Application not found.")
            return

        print(f"App: {b.basvuru_no}")
        print(f"DB Status (degerlendirme_durumu): {b.degerlendirme_durumu}")
        
        # Check preliminary items
        kriterler = KriterDegerlendirme.query.filter_by(basvuru_id=b.id).all()
        # Filter for the 12 preliminary items if they are distinguished, or typically they are just KriterDegerlendirme records.
        # Based on previous context, `KRITERLER` list in app.py defines them.
        
        completed_count = sum(1 for k in kriterler if k.sonuc)
        total_criteria = len(KRITERLER)
        
        print(f"Completed Criteria: {completed_count}/{total_criteria}")
        for k in kriterler:
            print(f"  - Kriter {k.kriter_no}: {k.sonuc}")

        # Check evaluators
        print(f"Evaluators: {[d.degerlendirici_adi for d in b.degerlendiriciler]}")

if __name__ == "__main__":
    debug_app_status()
