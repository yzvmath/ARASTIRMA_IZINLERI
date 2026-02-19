from app import app, db, kompleks_durum_metni_filter
from models import Basvuru

def verify_status_text():
    with app.app_context():
        # Get the specific application
        b = Basvuru.query.filter_by(basvuru_no="MEB.TT.2026.046207.02").first()
        if not b:
            print("Application not found.")
            return

        print(f"App: {b.basvuru_no}")
        print(f"DB Status: {b.degerlendirme_durumu}")
        print(f"Evaluators: {[d.degerlendirici_adi for d in b.degerlendiriciler]}")
        
        # Test the filter
        status_text = kompleks_durum_metni_filter(b)
        print(f"Calculated Status Text: {status_text}")
        
        if status_text == "Değerlendirici İncelemesinde":
             print("SUCCESS: Status text correctly identifies evaluator review.")
        else:
             print("FAILURE: Status text is incorrect.")

if __name__ == "__main__":
    verify_status_text()
