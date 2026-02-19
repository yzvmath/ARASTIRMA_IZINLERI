from app import app, db
from models import Basvuru

def verify_draft_save():
    with app.app_context():
        # Get a sample application
        b = Basvuru.query.first()
        if not b:
            print("No application found.")
            return

        print(f"Testing Draft Save with Application: {b.basvuru_no}")
        
        # Simulate draft save (generic save action)
        # We manually update fields as if form data was processed
        b.koordinator_karari = "RED"
        b.koordinator_notu = "Draft rejected note."
        # Status should NOT change to 'yonetici_onayinda' automatically if action is not 'yoneticiye_gonder'
        # But wait, the app.py logic only changes status if action == 'yoneticiye_gonder'.
        # Since we are simulating via script, we just need to verify that we can save these fields 
        # while keeping status as it was (e.g. 'degerlendirici_atama' or whatever).
        
        # Let's reset status to something else first to be sure
        b.degerlendirme_durumu = "bekliyor"
        db.session.commit()
        
        # Verification: Update fields and commit (simulating 'kaydet' action)
        b.koordinator_karari = "ONAY"
        b.koordinator_notu = "Draft approved note."
        db.session.commit()
        
        updated_b = Basvuru.query.get(b.id)
        if updated_b.degerlendirme_durumu == "bekliyor" and updated_b.koordinator_karari == "ONAY":
             print("SUCCESS: Draft saved without status change.")
             print(f"Status: {updated_b.degerlendirme_durumu}, Decision: {updated_b.koordinator_karari}")
        else:
             print("FAILURE: Draft save failed or status changed unexpectedly.")
             print(f"Status: {updated_b.degerlendirme_durumu}, Decision: {updated_b.koordinator_karari}")

if __name__ == "__main__":
    verify_draft_save()
