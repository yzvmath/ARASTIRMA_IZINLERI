from app import _get_val_robust, _normalize_key

# Mock data representing the problematic record from JSON
mock_record = {
  "detay_verileri": {
    "Ad Soyad (Link)": [
      {
        "text": "Ana Başvuru",
        "url": "..."
      },
      {
        "text": "Zeynep Hülya Konyalı - Araştırma Proje Bilgileri",
        "url": "..."
      },
      {
        "text": "Akademik Benlik Algısı Ölçeği ( Ölçek )",
        "url": "..."
      }
    ]
  },
  "tablo_verileri": {}
}

print("Testing _get_val_robust for Ad Soyad...")
result = _get_val_robust(mock_record, "Ad Soyad")
print(f"Result: '{result}'")

print("\nDebugging steps:")
val = mock_record["detay_verileri"].get("Ad Soyad (Link)")
print(f"Raw Value: {val}")

normalized_key = _normalize_key("Ad Soyad")
print(f"Normalized Key: {normalized_key}")

if "AD" in normalized_key and "SOYAD" in normalized_key:
    print("Key match: YES")
    for item in val:
        text = item.get("text", "")
        print(f"Checking text: '{text}'")
        if " - " in text:
            candidate = text.split(" - ")[0].strip()
            print(f"  Candidate: '{candidate}'")
            if " " in candidate and len(candidate) > 5 and len(candidate) < 50:
                print("  Match found!")
else:
    print("Key match: NO")
