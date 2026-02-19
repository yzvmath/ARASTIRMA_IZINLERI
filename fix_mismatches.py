import sqlite3

def fix_mismatches():
    conn = sqlite3.connect("degerlendirme.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    print("Fixing Status Mismatches...")
    
    # Select mismatches
    c.execute("SELECT id, basvuru_no FROM basvuru WHERE basvuru_durumu='Ön Değerlendirme Tamamlandı' AND degerlendirme_durumu IN ('bekliyor', 'devam')")
    rows = c.fetchall()
    
    count = 0
    for row in rows:
        print(f"Fixing ID {row['id']} ({row['basvuru_no']})...")
        c.execute("UPDATE basvuru SET degerlendirme_durumu='tamamlandi' WHERE id=?", (row['id'],))
        count += 1
            
    conn.commit()
    conn.close()
    
    if count == 0:
        print("No mismatches found to fix.")
    else:
        print(f"Fixed {count} records.")

if __name__ == "__main__":
    fix_mismatches()
