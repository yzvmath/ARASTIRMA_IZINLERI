import sqlite3

def check_pending_school_selection():
    conn = sqlite3.connect("degerlendirme.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    print("Checking for ANY application in 'okul_secimi' state...")
    c.execute("SELECT id, basvuru_no, degerlendirme_durumu, yonetici_notu, secilen_okul FROM basvuru WHERE degerlendirme_durumu='okul_secimi'")
    rows = c.fetchall()
    
    if rows:
        for row in rows:
            print(f"--- Application {row['basvuru_no']} (ID: {row['id']}) ---")
            print(f"Durum: {row['degerlendirme_durumu']}")
            print(f"Secilen Okul: {row['secilen_okul']}")
    else:
        print("No applications found in 'okul_secimi' state.")
        
    conn.close()

if __name__ == "__main__":
    check_pending_school_selection()
