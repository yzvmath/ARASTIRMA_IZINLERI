# -*- coding: utf-8 -*-
import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "degerlendirme.db")

def migrate():
    """Veritabanına yeni eklenen sütunları ekler."""
    if not os.path.exists(DB_PATH):
        print(f"Veritabanı bulunamadı: {DB_PATH}")
        print("Uygulama ilk kez çalıştırıldığında otomatik olarak oluşturulacaktır.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Veritabanı guncelleniyor: 'diger_ekler' sutunu ekleniyor...")
        cursor.execute("ALTER TABLE basvuru ADD COLUMN diger_ekler TEXT")
        conn.commit()
        print("OK: Guncelleme basariyla tamamlandi!")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("INFO: 'diger_ekler' sutunu zaten mevcut.")
        else:
            print(f"ERROR: Guncelleme hatasi: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
