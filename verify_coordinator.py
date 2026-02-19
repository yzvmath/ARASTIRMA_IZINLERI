from app import app, db
from models import Basvuru

def verify_coordinator_decision():
    with app.app_context():
        # Get a sample application
        b = Basvuru.query.first()
        if not b:
            print("No application found.")
            return

        print(f"Testing with Application: {b.basvuru_no}")
        
        # Simulate coordinator decision
        b.koordinator_karari = "RED"
        b.koordinator_notu = "Eksikler var ancak yoneticiye arz ediyorum."
        b.degerlendirme_durumu = "yonetici_onayinda"
        
        db.session.commit()
        print("Updated coordinator decision to 'RED' and status to 'yonetici_onayinda'.")
            
        # Verify
        updated_b = Basvuru.query.get(b.id)
        print(f"Verification: Status: {updated_b.degerlendirme_durumu}, Coord Decision: {updated_b.koordinator_karari}, Note: {updated_b.koordinator_notu}")

if __name__ == "__main__":
    verify_coordinator_decision()
