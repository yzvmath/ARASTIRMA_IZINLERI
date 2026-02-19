import sqlite3

def migrate():
    conn = sqlite3.connect("degerlendirme.db")
    c = conn.cursor()
    
    print("Migrating database for coordinator columns...")
    
    try:
        c.execute("ALTER TABLE basvuru ADD COLUMN koordinator_karari TEXT")
        print("Added 'koordinator_karari' column.")
    except sqlite3.OperationalError:
        print("'koordinator_karari' column already exists.")
        
    try:
        c.execute("ALTER TABLE basvuru ADD COLUMN koordinator_notu TEXT")
        print("Added 'koordinator_notu' column.")
    except sqlite3.OperationalError:
        print("'koordinator_notu' column already exists.")
        
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
