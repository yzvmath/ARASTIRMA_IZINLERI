def test_status_mapping():
    test_cases = [
        ("ÖN DEĞERLENDİRME TAMAMLANDI", "tamamlandi"),
        ("ÖN DEĞERLENDIRME TAMAMLANDI", "tamamlandi"), # I instead of İ
        ("Ön Değerlendirme Tamamlandı", "tamamlandi"),
        ("Ön İnceleme/Onay Bekliyor", "devam"),
        ("İşlem Bekliyor", "bekliyor"),
        ("Bilinmeyen Durum", "bekliyor"), 
        ("SONUÇLANDI", "tamamlandi"),
        ("KABUL EDİLDİ", "tamamlandi")
    ]
    
    print("Testing Status Mapping Logic...")
    print("-" * 50)
    
    all_passed = True
    for mebbis_input, expected in test_cases:
        mebbis_durum = mebbis_input.upper()
        yeni_veri = {"basvuru_durumu": mebbis_input}
        
        # LOGIC FROM app.py
        if "TAMAMLANDI" in mebbis_durum or "TAMAMLAND" in mebbis_durum:
             yeni_veri["degerlendirme_durumu"] = "tamamlandi"
        elif "ONAY" in mebbis_durum:
            yeni_veri["degerlendirme_durumu"] = "devam"
        elif "TAMAM" in mebbis_durum or "SONUÇ" in mebbis_durum or "KABUL" in mebbis_durum:
            yeni_veri["degerlendirme_durumu"] = "tamamlandi"
        else:
             yeni_veri["degerlendirme_durumu"] = "bekliyor"
        # END LOGIC
        
        result = yeni_veri["degerlendirme_durumu"]
        
        if result == expected:
            print(f"PASS: '{mebbis_input}' -> '{result}'")
        else:
            print(f"FAIL: '{mebbis_input}' -> Expected '{expected}', got '{result}'")
            all_passed = False
            
    print("-" * 50)
    if all_passed:
        print("ALL TESTS PASSED.")
    else:
        print("SOME TESTS FAILED.")

if __name__ == "__main__":
    test_status_mapping()
