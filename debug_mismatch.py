import sqlite3

def check_mismatches():
    conn = sqlite3.connect("degerlendirme.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    print("Checking for Status Mismatches...")
    print("Looking for: basvuru_durumu='Ön Değerlendirme Tamamlandı' BUT degerlendirme_durumu IN ['bekliyor', 'devam']")
    
    c.execute("SELECT id, basvuru_no, basvuru_durumu, degerlendirme_durumu, yonetici_notu FROM basvuru")
    rows = c.fetchall()
    
    count = 0
    for row in rows:
        b_durum = row['basvuru_durumu']
        d_durum = row['degerlendirme_durumu']
        
        # Check if MEBBIS says completed but Internal says waiting/continuing
        if b_durum == 'Ön Değerlendirme Tamamlandı' and d_durum in ['bekliyor', 'devam']:
            print(f"--- Mismatch Found: ID {row['id']} ({row['basvuru_no']}) ---")
            print(f"MEBBIS Status: {b_durum}")
            print(f"Internal Status: {d_durum}")
            count += 1
            
    if count == 0:
        print("No obvious mismatches found based on simple criteria.")
    else:
        print(f"Found {count} mismatches.")

    conn.close()

if __name__ == "__main__":
    check_mismatches()
