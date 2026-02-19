import requests
import sqlite3

BASE_URL = "http://127.0.0.1:5000"
TEST_ID = 5

def reset_to_okul_secimi():
    conn = sqlite3.connect("degerlendirme.db")
    c = conn.cursor()
    c.execute("UPDATE basvuru SET degerlendirme_durumu='okul_secimi', secilen_okul='OLD_SCHOOL' WHERE id=?", (TEST_ID,))
    conn.commit()
    conn.close()
    print(f"Reset ID {TEST_ID} to 'okul_secimi'")

def test_school_selection():
    reset_to_okul_secimi()
    
    print("Sending POST to /okul-sec...")
    new_school = "NEW TEST SCHOOL"
    resp = requests.post(f"{BASE_URL}/basvuru/{TEST_ID}/okul-sec", data={"secilen_okul": new_school})
    
    print(f"Response Status: {resp.status_code}")
    
    conn = sqlite3.connect("degerlendirme.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT degerlendirme_durumu, secilen_okul FROM basvuru WHERE id=?", (TEST_ID,))
    row = c.fetchone()
    conn.close()
    
    print(f"DB Status: {row['degerlendirme_durumu']}")
    print(f"DB School: {row['secilen_okul']}")
    
    if row['degerlendirme_durumu'] == 'onaylandi' and row['secilen_okul'] == new_school:
        print("PASS: Backend logic works.")
    else:
        print("FAIL: Backend logic failed.")

if __name__ == "__main__":
    test_school_selection()
