import sqlite3

def migrate():
    conn = sqlite3.connect("degerlendirme.db")
    c = conn.cursor()
    
    print("Migrating database...")
    
    try:
        c.execute("ALTER TABLE basvuru_degerlendirici ADD COLUMN karar TEXT")
        print("Added 'karar' column.")
    except sqlite3.OperationalError:
        print("'karar' column already exists.")
        
    try:
        c.execute("ALTER TABLE basvuru_degerlendirici ADD COLUMN aciklama TEXT")
        print("Added 'aciklama' column.")
    except sqlite3.OperationalError:
        print("'aciklama' column already exists.")
        
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
