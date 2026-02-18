import json
import os

json_path = r"d:\ARASTIMA_IZINLERI\mebbis_verileri_20260218_114323.json"

if not os.path.exists(json_path):
    print(f"File not found: {json_path}")
    exit(1)

try:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Total records in JSON: {len(data)}")
    
    found = False
    for i, item in enumerate(data):
        # Try to find ID in tablo_verileri
        tablo = item.get("tablo_verileri", {})
        basvuru_no = tablo.get("BAŞVURU NO")
        if not basvuru_no:
            basvuru_no = tablo.get("BAŞVURU\nNO") # Try checking with newline
            
        print(f"{i+1}: {basvuru_no}")

        if i == 0:
             print("Dumping VALID record (Index 0):")
             detay = item.get("detay_verileri", {})
             for k, v in detay.items():
                print(f"Key: '{k}'")
                if "TELEFON" in k.upper() or "CEP" in k.upper():
                    print(f"  POTENTIAL PHONE: {v}")
             
             print("TABLO VERILERI (Index 0):")
             for k, v in tablo.items():
                 print(f"Tablo Key: '{k}': {v}")
        
        if basvuru_no == "MEB.TT.2025.044260.02":
            found = True
            print("Found target record in JSON!")
            print("-" * 30)
            detay = item.get("detay_verileri", {})
            print("DETAY VERILERI IS EMPTY!" if not detay else "Detay Verileri found")
            
            print("TABLO VERILERI (Target):")
            for k, v in tablo.items():
                print(f"Key: '{k}', Value: '{v}'")
            print("-" * 30)
            
    if not found:
        print("\nTarget record MEB.TT.2025.044260.02 NOT FOUND in JSON.")

except Exception as e:
    print(f"Error: {e}")
