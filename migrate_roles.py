import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'degerlendirme.db')

def migrate_roles():
    if not os.path.exists(DB_PATH):
        print(f"Veritabanı bulunamadı: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if 'rol' column already exists
        cursor.execute("PRAGMA table_info(degerlendirici)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'rol' not in columns:
            print("Ekleniyor: 'rol' sütunu 'degerlendirici' tablosuna...")
            cursor.execute("ALTER TABLE degerlendirici ADD COLUMN rol VARCHAR(50) DEFAULT 'degerlendirici'")
            conn.commit()
            print("Görev başarılı: 'rol' sütunu eklendi. Mevcut kayıtlar 'degerlendirici' olarak ayarlandı.")
        else:
            print("'rol' sütunu zaten mevcut.")
            
    except Exception as e:
        print(f"Hata: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_roles()
