from app import app, db
from models import Basvuru, BasvuruDegerlendirici

def verify_decision():
    with app.app_context():
        # Get a sample application
        b = Basvuru.query.first()
        if not b:
            print("No application found.")
            return

        print(f"Testing with Application: {b.basvuru_no}")
        
        # Assign an evaluator if none exists
        if not b.degerlendiriciler:
            print("Assigning a dummy evaluator...")
            bd = BasvuruDegerlendirici(basvuru_id=b.id, degerlendirici_adi="Test Değerlendirici", karar="ONAY")
            db.session.add(bd)
            db.session.commit()
            print("Assigned 'Test Değerlendirici' with decision 'ONAY'.")
        else:
            # Update the first evaluator's decision
            bd = b.degerlendiriciler[0]
            print(f"Updating evaluator '{bd.degerlendirici_adi}' decision to 'RED'...")
            bd.karar = "RED"
            db.session.commit()
            print("Updated decision to 'RED'.")
            
        # Verify
        updated_bd = BasvuruDegerlendirici.query.filter_by(basvuru_id=b.id).first()
        print(f"Verification: Evaluator: {updated_bd.degerlendirici_adi}, Decision: {updated_bd.karar}")

if __name__ == "__main__":
    verify_decision()
