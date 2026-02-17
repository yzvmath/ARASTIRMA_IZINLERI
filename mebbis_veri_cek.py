# -*- coding: utf-8 -*-
"""
MEBBIS Araştırma İzni Veri Çekme Scripti
==========================================
Bu script MEBBIS sistemine giriş yapıp, araştırma izinleri
sayfasındaki bekleyen işlemleri ve detaylarını Excel'e aktarır.

Kullanım:
    python mebbis_veri_cek.py

Gereksinimler:
    pip install selenium openpyxl webdriver-manager
"""

import time
from concurrent.futures import ThreadPoolExecutor
import os
import sys
import re
import json
from datetime import datetime
import traceback
import requests
import shutil
import subprocess

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from webdriver_manager.chrome import ChromeDriverManager
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side


# ─── Ayarlar ──────────────────────────────────────────────────────────────────
TC_KIMLIK = "28585457194"
MEBBIS_URL = "https://mebbis.meb.gov.tr/ssologinBIDB.aspx?id=155"
HEDEF_URL = "https://arastirmaizinleri.meb.gov.tr/panel/arastirma-uygulamalari/bekleyen-islemler"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))  # Scriptin bulunduğu klasör
ZAMAN_DAMGASI = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"mebbis_verileri_{ZAMAN_DAMGASI}.xlsx")
# ─────────────────────────────────────────────────────────────────────────────

# Detay sayfasından çekilecek alanlar (sıralı)
DETAY_ALANLARI = [
    # ── Başvuru Bilgileri ──
    "Başvuru Numarası",
    "Başvuru Tarihi",
    "Başvuru Durumu",
    # ── Kişisel Bilgiler ──
    "TC Kimlik No",
    "Ad Soyad",
    "Telefon",
    "E-Posta",
    "Adres",
    # ── Başvuru Bilgileri (2) ──
    "Başvuru Şekli",
    "Başvurunun Yapıldığı Ülke",
    "Meslek",
    "Çalıştığı Kurum",
    # ── Araştırma Bilgileri ──
    "Araştırmanın Adı",
    "Eğitim Teknolojileri İle İlgili",
    "Araştırmanın Niteliği",
    "Akademik Başarı Ölçme",
    "Araştırmanın Konusu ve İlişkili Konular",
    "Anahtar Kelimeler",
    "Araştırmanın Yazım Dili",
    # ── Uygulama Bilgileri ──
    "Uygulama Yapılacak İl Sayısı",
    "Çalışma Grubu",
    "Teşkilat Türü",
    "Uygulama Yapılacak MEB Teşkilatı",
    "Uygulama Okul/Kurum Sayısı",
    "Özel Bilgiler",
    "Uygulama Süresi",
    # ── Belgeler ──
    "Araştırma Proje Bilgileri (Link)",
    "Veri Toplama Aracı (Link)",
    "Taahhütname (Link)",
    "Etik Kurul Onay (Link)",
    "Bilgilendirme ve Gönüllü Katılım Formu (Link)",
    "Veli Onam Formu (Link)",
    "Ölçek Kullanım İzni (Link)",
    "Diğer Ekler",
]

# Belgelerin indirileceği ana klasör
# Scriptin bulunduğu dizini garanti altına al
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOC_BASE_DIR = os.path.join(SCRIPT_DIR, "static", "belgeler")

print(f"\n--- Sistem Bilgileri")
print(f"- Çalisma dizini: {os.getcwd()}")
print(f"- Script dizini : {SCRIPT_DIR}")
print(f"- Belge deposu  : {DOC_BASE_DIR}")

if not os.path.exists(DOC_BASE_DIR):
    try:
        os.makedirs(DOC_BASE_DIR, exist_ok=True)
        print("  [OK] Belge deposu olusturuldu.")
    except Exception as e:
        print(f"  [HATA] Belge deposu olusturuldu: {e}")
else:
    print("  [BILGI] Belge deposu zaten mevcut.")


def belge_indir(url, klasor_adi, dosya_adi, driver):
    """
    Belgeyi Selenium oturum çerezlerini kullanarak indirir.
    Yerel yolu döndürür (static/belgeler/...).
    """
    if not url or url == "#" or "javascript:" in url:
        return None

    try:
        # Klasör oluştur (Başvuru No'ya göre)
        temiz_klasor_adi = re.sub(r'[\\/:*?"<>|]', '_', klasor_adi)
        hedef_klasor = os.path.join(DOC_BASE_DIR, temiz_klasor_adi)
        if not os.path.exists(hedef_klasor):
            os.makedirs(hedef_klasor, exist_ok=True)

        # Dosya adını temizle ve uzantıyı koru, başvuru nosunu ekle
        temiz_dosya_adi = re.sub(r'[\\/:*?"<>|]', '_', dosya_adi)
        if not any(temiz_dosya_adi.lower().endswith(ext) for ext in ['.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx', '.xls', '.xlsx']):
            ext = os.path.splitext(url.split('?')[0])[1]
            if not ext: ext = ".pdf"
            temiz_dosya_adi += ext
        
        # Dosya adının başına başvuru no ekle (İsteğiniz üzerine: No_DosyaAdi.pdf)
        temiz_dosya_adi = f"{temiz_klasor_adi}_{temiz_dosya_adi}"
        
        hedef_yol = os.path.join(hedef_klasor, temiz_dosya_adi)

        session = requests.Session()
        for cookie in driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'])

        user_agent = driver.execute_script("return navigator.userAgent")
        headers = {"User-Agent": user_agent}

        response = session.get(url, headers=headers, stream=True, timeout=30)
        if response.status_code == 200:
            with open(hedef_yol, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Flask için relative path (static/... formatında)
            # Başına slash eklemeden döndürüyoruz, template içinde yönetilecek
            rel_path = f"static/belgeler/{temiz_klasor_adi}/{temiz_dosya_adi}"
            return rel_path
        else:
            print(f"      [UYARI] Indirme hatasi (HTTP {response.status_code}): {dosya_adi}")
            return None
    except Exception as e:
        print(f"      [HATA] Belge indirilemedi ({dosya_adi}): {e}")
        return None


def tarayici_baslat():
    """Chrome tarayiciyi baslatir."""
    print("\n--- Chrome tarayici baslatiliyor...")
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chrome_options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def giris_yap(driver):
    """
    MEBBIS giriş sayfasını açar, TC kimlik numarasını otomatik doldurur
    ve kullanıcının oturumu açmasını bekler.
    """
    print(f"\n- MEBBIS giris sayfasi aciliyor: {MEBBIS_URL}")
    driver.get(MEBBIS_URL)
    time.sleep(3)

    # TC kimlik numarasını otomatik doldur
    try:
        tc_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "txtKullaniciAd"))
        )
        tc_input.clear()
        tc_input.send_keys(TC_KIMLIK)
        print(f"   OK: TC Kimlik No otomatik girildi: {TC_KIMLIK}")
    except TimeoutException:
        print("   UYARI: Kullanici adi alani bulunamadi, manuel girin.")

    print("\n" + "=" * 60)
    print("  LUTFEN OTURUMU ACIN")
    print("     (Guvenlik kodu + Sifre + Iki asamali dogrulama)")
    print("     TC Kimlik No otomatik girildi.")
    print("=" * 60)
    print("\n... Oturumu actiktan sonra buraya donup ENTER'a basin...")
    print()

    input("-> Oturum acildiysa ENTER'a basin: ")
    print("\nOK: Devam ediliyor...")
    time.sleep(1)


def hedef_sayfaya_git(driver):
    """Arastirma izinleri bekleyen islemler sayfasina gider."""
    print(f"\n- Hedef sayfaya gidiliyor: {HEDEF_URL}")
    driver.get(HEDEF_URL)
    time.sleep(5)
    print(f"   Mevcut URL: {driver.current_url}")
    print(f"   Sayfa Basligi: {driver.title}")


def ana_tablo_bul(driver):
    """Sayfadaki ana veri tablosunu bulur."""
    seciciler = [
        "table.table",
        "table.dataTable",
        "table[id*='Grid']",
        "table[id*='grid']",
        "div.table-responsive table",
        "table",
    ]
    for secici in seciciler:
        try:
            tablolar = driver.find_elements(By.CSS_SELECTOR, secici)
            for tablo in tablolar:
                satirlar = tablo.find_elements(By.TAG_NAME, "tr")
                if len(satirlar) >= 2:
                    tablo_id = tablo.get_attribute("id") or "isimsiz"
                    print(f"   OK: Tablo bulundu (id: {tablo_id}, {len(satirlar)} satir)")
                    return tablo
        except Exception:
            pass
    print("   HATA: Uygun tablo bulunamadi!")
    return None


def tablo_basliklarini_oku(tablo):
    """Tablonun başlık satırını okur."""
    basliklar = []
    try:
        thead = tablo.find_elements(By.TAG_NAME, "thead")
        if thead:
            baslik_hucreleri = thead[0].find_elements(By.TAG_NAME, "th")
            if not baslik_hucreleri:
                baslik_hucreleri = thead[0].find_elements(By.TAG_NAME, "td")
        else:
            ilk_satir = tablo.find_elements(By.TAG_NAME, "tr")[0]
            baslik_hucreleri = ilk_satir.find_elements(By.TAG_NAME, "th")
            if not baslik_hucreleri:
                baslik_hucreleri = ilk_satir.find_elements(By.TAG_NAME, "td")

        for hucre in baslik_hucreleri:
            metin = hucre.text.strip()
            if metin:
                basliklar.append(metin)
            else:
                basliklar.append(f"Sütun_{len(basliklar) + 1}")
    except Exception as e:
        print(f"   HATA: Baslik okuma hatasi: {e}")
    return basliklar


def tablo_satirlarini_oku(tablo):
    """Tablodaki veri satirlarini ve detay butonlarini okur."""
    satirlar_verisi = []
    try:
        tbody = tablo.find_elements(By.TAG_NAME, "tbody")
        if tbody:
            satirlar = tbody[0].find_elements(By.TAG_NAME, "tr")
        else:
            tum_satirlar = tablo.find_elements(By.TAG_NAME, "tr")
            satirlar = tum_satirlar[1:] if len(tum_satirlar) > 1 else []

        for satir in satirlar:
            hucreler = satir.find_elements(By.TAG_NAME, "td")
            if not hucreler:
                continue

            hucre_metinleri = []
            detay_butonu = None
            degerlendir_butonu = None

            for hucre in hucreler:
                metin = hucre.text.strip()
                hucre_metinleri.append(metin)

                # Detay butonunu ara
                if not detay_butonu:
                    linkler = hucre.find_elements(By.TAG_NAME, "a")
                    butonlar = hucre.find_elements(By.TAG_NAME, "button")
                    tum_el = linkler + butonlar

                    for el in tum_el:
                        el_metin = (el.text or "").strip().lower()
                        el_title = (el.get_attribute("title") or "").lower()
                        el_class = (el.get_attribute("class") or "").lower()
                        el_onclick = (el.get_attribute("onclick") or "").lower()

                        if any(k in el_metin or k in el_title or k in el_class or k in el_onclick
                               for k in ["detay", "goruntule", "incele", "goster", "detail", "view", "show", "eye", "search", "basvuru_detay"]):
                            detay_butonu = el
                            break

                # Degerlendir butonunu ara
                if not degerlendir_butonu:
                    try:
                        ikon = hucre.find_element(By.CSS_SELECTOR, "i.ti-checkbox, i[class*='ti-checkbox']")
                        if ikon:
                            degerlendir_butonu = ikon.find_element(By.XPATH, "./ancestor::a[1] | ./ancestor::button[1]")
                    except:
                        pass

            # Fallback for detay_butonu
            if not detay_butonu:
                try:
                    all_links = satir.find_elements(By.TAG_NAME, "a")
                    if all_links:
                        detay_butonu = all_links[-1]
                except: pass

            satirlar_verisi.append({
                "hucre_metinleri": hucre_metinleri,
                "detay_butonu": detay_butonu,
                "degerlendir_butonu": degerlendir_butonu,
            })
    except Exception as e:
        print(f"   HATA: Satir okuma hatasi: {e}")
    return satirlar_verisi


def _linkleri_oku(parent_el, span_el):
    """
    Bir belge alanındaki linkleri [{"text": "...", "url": "..."}] listesi olarak döndürür.
    Önce parent_p içindeki <a> etiketlerini, bulamazsa ancestor div içindeki <a>'ları arar.
    Daha geniş arama: mb-3, card-body, col, row gibi ancestor'lara da bakar.
    """
    linkler_sonuc = []
    try:
        # Önce doğrudan parent'taki linkleri ara
        linkler = parent_el.find_elements(By.TAG_NAME, "a")
        if not linkler:
            # Daha geniş bir alanda ara - birden fazla ancestor seçici dene
            ancestor_seciciler = [
                "./ancestor::div[contains(@class,'mb-3')]",
                "./ancestor::div[contains(@class,'card-body')]",
                "./ancestor::div[contains(@class,'col')]",
                "./ancestor::div[contains(@class,'row')][1]",
                "./ancestor::div[2]",  # İki üst div
            ]
            for secici in ancestor_seciciler:
                try:
                    parent_div = span_el.find_element(By.XPATH, secici)
                    linkler = parent_div.find_elements(By.TAG_NAME, "a")
                    if linkler:
                        break
                except NoSuchElementException:
                    continue
        for lnk in linkler:
            url = (lnk.get_attribute("href") or "").strip()
            metin = (lnk.text or "").strip()
            if url and url != "#" and "javascript:" not in url:
                if not metin:
                    metin = "Belge"
                linkler_sonuc.append({"text": metin, "url": url})
    except Exception:
        pass
    return linkler_sonuc if linkler_sonuc else ""


def detay_sayfasini_oku(driver):
    """Detay sayfasindaki tum bilgileri okur ve belge linklerini yakalar."""
    veriler = {}
    time.sleep(2)
    try:
        # P etiketlerini oku (Etiket: Deger formatı)
        ps = driver.find_elements(By.CSS_SELECTOR, "p.ps-4")
        for p in ps:
            try:
                span = p.find_element(By.TAG_NAME, "span")
                etiket = span.text.strip().replace(":", "")
                deger = p.text.replace(span.text, "").strip()
                
                # Link var mı kontrol et
                linkler = _linkleri_oku(p, span)
                if linkler:
                    veriler[etiket + " (Link)"] = linkler
                else:
                    veriler[etiket] = deger
            except:
                continue

        # Kartlar icindeki diger alanlari ve linkleri de tara
        cards = driver.find_elements(By.CLASS_NAME, "card")
        for card in cards:
            all_links = card.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                href = link.get_attribute("href")
                if href and ("download" in href.lower() or "file" in href.lower() or ".pdf" in href.lower() or "basvuru-belge" in href.lower()):
                    text = link.text.strip() or "Belge"
                    if "Diğer Ekler" not in veriler: veriler["Diğer Ekler"] = []
                    if not any(l["url"] == href for l in veriler["Diğer Ekler"]):
                        veriler["Diğer Ekler"].append({"text": text, "url": href})

        # Baslik (H1, H3 gibi) ara - Genelde Proje Adi buradadir
        headers = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5")
        for h in headers:
            txt = h.text.strip()
            if len(txt) > 10 and "Detay" not in txt and "Bilgi" not in txt:
                veriler["Baslik_Adi"] = txt
                break

        # Uygulama Bilgileri Tablosu
        try:
            tablo = driver.find_element(By.ID, "ozetUygulamaBilgileriTable")
            rows = tablo.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) == 2:
                    k = cols[0].text.strip().replace(":", "")
                    v = cols[1].text.strip()
                    veriler[k] = v
                elif len(cols) == 6: # Coklu satir
                    if "Uygulama Bilgileri" not in veriler: veriler["Uygulama Bilgileri"] = []
                    veriler["Uygulama Bilgileri"].append([c.text.strip() for c in cols])
        except: pass

    except Exception as e:
        print(f"      [!] Detay okuma hatasi: {e}")
    
    return veriler


def sayfalama_kontrol(driver):
    """Sayfalama varsa sonraki sayfaya geçer."""
    seciciler = [
        "a.page-link",
        "li.page-item a",
        "a[aria-label='Next']",
        ".pagination a",
        "a.next",
        "a.paginate_button.next",
    ]
    for secici in seciciler:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, secici)
            for el in elements:
                metin = el.text.strip().lower()
                aria = (el.get_attribute("aria-label") or "").lower()
                if any(k in metin or k in aria for k in ["next", "sonraki", "ileri", "›", "»", ">"]):
                    parent = el.find_element(By.XPATH, "..")
                    parent_class = (parent.get_attribute("class") or "").lower()
                    if "disabled" not in parent_class:
                        print("   📄 Sonraki sayfaya geçiliyor...")
                        el.click()
                        time.sleep(4)
                        return True
        except Exception:
            pass
    return False


def _hucre_yaz(ws, row, col, deger, veri_font, link_font, veri_alignment, ince_border):
    """
    Bir hücreye değer yazar. Değer link listesi ise tıklanabilir hyperlink yapar.
    - Tek link: HYPERLINK formülü ile tıklanabilir metin
    - Çoklu link: Her biri ayrı satırda HYPERLINK formülü (ilk linke hyperlink)
    - Normal metin: Düz metin olarak yazar
    """
    hucre = ws.cell(row=row, column=col)
    hucre.alignment = veri_alignment
    hucre.border = ince_border

    if isinstance(deger, list) and deger and isinstance(deger[0], dict):
        # Link listesi
        if len(deger) == 1:
            # Tek link → tıklanabilir hyperlink
            link = deger[0]
            hucre.value = f'=HYPERLINK("{link["url"]}", "{link["text"].replace(chr(34), chr(39))}")'  # " → '
            hucre.font = link_font
        else:
            # Çoklu link → ilk linke hyperlink, diğerlerini alt satırlara yaz
            ilk = deger[0]
            hucre.hyperlink = ilk["url"]
            hucre.value = "\n".join(lnk["text"] for lnk in deger)
            hucre.font = link_font
    else:
        if isinstance(deger, (list, dict)):
            # Liste veya dict ise (tablo verisi gibi) metne dönüştür
            if isinstance(deger, list) and deger and isinstance(deger[0], list):
                # Tablo formatındaki listeler
                hucre.value = "\n".join([" | ".join([str(c) for c in row]) for row in deger])
            else:
                hucre.value = str(deger)
        else:
            hucre.value = deger if deger else ""
        hucre.font = veri_font


def excel_olustur(basliklar, tum_satirlar):
    """
    Tüm verileri tek satır halinde Excel'e yazar.
    Ana tablo sütunları + detay sütunları yan yana.
    Link alanları tıklanabilir hyperlink olarak yazılır.
    """
    print(f"\n- Excel dosyasi olusturuluyor: {OUTPUT_FILE}")

    wb = Workbook()
    ws = wb.active
    ws.title = "Bekleyen İşlemler"

    # ─── Stiller ─────────────────────────────────────────────────────────
    baslik_font = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
    baslik_fill_ana = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    baslik_fill_kisisel = PatternFill(start_color="548235", end_color="548235", fill_type="solid")
    baslik_fill_basvuru = PatternFill(start_color="BF8F00", end_color="BF8F00", fill_type="solid")
    baslik_fill_arastirma = PatternFill(start_color="C55A11", end_color="C55A11", fill_type="solid")
    baslik_fill_uygulama = PatternFill(start_color="7030A0", end_color="7030A0", fill_type="solid")
    baslik_fill_belge = PatternFill(start_color="808080", end_color="808080", fill_type="solid")
    baslik_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    veri_font = Font(name="Calibri", size=10)
    link_font = Font(name="Calibri", size=10, color="0563C1", underline="single")
    veri_alignment = Alignment(vertical="center", wrap_text=True)
    ince_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )

    # ─── Renk haritası (detay alan adına göre) ───────────────────────────
    def detay_renk(alan):
        if alan in ["Başvuru Numarası", "Başvuru Tarihi", "Başvuru Durumu"]:
            return baslik_fill_ana
        elif alan in ["TC Kimlik No", "Ad Soyad", "Telefon", "E-Posta", "Adres"]:
            return baslik_fill_kisisel
        elif alan in ["Başvuru Şekli", "Başvurunun Yapıldığı Ülke", "Meslek", "Çalıştığı Kurum"]:
            return baslik_fill_basvuru
        elif alan in ["Araştırmanın Adı", "Eğitim Teknolojileri İle İlgili",
                       "Araştırmanın Niteliği", "Akademik Başarı Ölçme",
                       "Araştırmanın Konusu ve İlişkili Konular",
                       "Anahtar Kelimeler", "Araştırmanın Yazım Dili"]:
            return baslik_fill_arastirma
        elif alan in ["Uygulama Yapılacak İl Sayısı", "Çalışma Grubu", "Teşkilat Türü",
                       "Uygulama Yapılacak MEB Teşkilatı", "Uygulama Okul/Kurum Sayısı",
                       "Özel Bilgiler", "Uygulama Süresi"]:
            return baslik_fill_uygulama
        else:
            return baslik_fill_belge

    # ─── Başlıklar: Ana tablo + Detay alanları ──────────────────────────
    ana_basliklar = list(basliklar)
    tum_basliklar = list(ana_basliklar) + list(DETAY_ALANLARI)

    # Ekstra detay alanları (DETAY_ALANLARI'nda olmayan ama veride bulunan)
    ekstra_alanlar = []
    for satir in tum_satirlar:
        for key in satir.get("detay_verileri", {}):
            if key not in DETAY_ALANLARI and key not in ekstra_alanlar:
                ekstra_alanlar.append(key)
    tum_basliklar.extend(ekstra_alanlar)

    # Başlık satırını yaz
    for col, baslik in enumerate(tum_basliklar, 1):
        hucre = ws.cell(row=1, column=col, value=baslik)
        hucre.font = baslik_font
        hucre.alignment = baslik_alignment
        hucre.border = ince_border

        if col <= len(ana_basliklar):
            hucre.fill = baslik_fill_ana
        else:
            detay_alan = baslik
            hucre.fill = detay_renk(detay_alan)

    # ─── Verileri yaz ────────────────────────────────────────────────────
    for row_idx, satir in enumerate(tum_satirlar, 2):
        hucre_verileri = satir["hucre_metinleri"]
        detay_verileri = satir.get("detay_verileri", {})

        # Ana tablo sütunları
        for col, deger in enumerate(hucre_verileri, 1):
            if col <= len(ana_basliklar):
                hucre = ws.cell(row=row_idx, column=col, value=deger)
                hucre.font = veri_font
                hucre.alignment = veri_alignment
                hucre.border = ince_border

        # Detay sütunları (sabit alanlar)
        offset = len(ana_basliklar)
        for d_col, d_alan in enumerate(DETAY_ALANLARI):
            deger = detay_verileri.get(d_alan, "")
            col_num = offset + d_col + 1
            _hucre_yaz(ws, row_idx, col_num, deger, veri_font, link_font, veri_alignment, ince_border)

        # Ekstra detay alanları
        offset2 = offset + len(DETAY_ALANLARI)
        for e_col, e_alan in enumerate(ekstra_alanlar):
            deger = detay_verileri.get(e_alan, "")
            col_num = offset2 + e_col + 1
            _hucre_yaz(ws, row_idx, col_num, deger, veri_font, link_font, veri_alignment, ince_border)

    # ─── Sütun genişlikleri ──────────────────────────────────────────────
    for col_idx in range(1, len(tum_basliklar) + 1):
        max_len = 0
        for row_idx in range(1, len(tum_satirlar) + 2):
            val = ws.cell(row=row_idx, column=col_idx).value
            if val:
                max_len = max(max_len, min(len(str(val)), 40))
        col_letter = ws.cell(row=1, column=col_idx).column_letter
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # Filtre ve dondurma
    if tum_basliklar:
        ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = "A2"

    wb.save(OUTPUT_FILE)
    print(f"   OK: Excel dosyasi kaydedildi: {OUTPUT_FILE}")
    return OUTPUT_FILE


def json_export(basliklar, tum_satirlar, silent=False):
    """
    Tüm verileri JSON dosyasına aktarır.
    Flask uygulamasına veri aktarmak için kullanılır.
    """
    json_dosya = OUTPUT_FILE.replace(".xlsx", ".json")
    if not silent: print(f"\n- JSON dosyasi olusturuluyor: {json_dosya}")

    sonuc = []
    for satir in tum_satirlar:
        kayit = {
            "tablo_verileri": dict(zip(basliklar, satir.get("hucre_metinleri", []))),
            "detay_verileri": satir.get("detay_verileri", {}),
        }
        sonuc.append(kayit)

    with open(json_dosya, "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=2)

    if not silent:
        print(f"   OK: JSON dosyasi kaydedildi: {json_dosya}")
    return json_dosya


def main():
    print("=" * 60)
    print("   MEBBIS Araştırma İzni - Bekleyen İşlemler")
    print("   Veri Çekme Scripti")
    print("=" * 60)

    # 1) Tarayıcıyı başlat
    driver = tarayici_baslat()

    try:
        # 2) Giriş yap
        giris_yap(driver)

        # 3) Hedef sayfaya git
        hedef_sayfaya_git(driver)

        # 4) Oturum kontrolü
        if "oturum" in driver.page_source.lower() and "bulunamadı" in driver.page_source.lower():
            print("\nUYARI: Oturum gecersiz gorunuyor. Tekrar deneniyor...")
            time.sleep(2)
            driver.get(HEDEF_URL)
            time.sleep(5)

        # 5) Ana tabloyu bul
        print("\n- Sayfa analiz ediliyor...")
        tablo = ana_tablo_bul(driver)
        if not tablo:
            print("\n- Tablo bulunamadi!")
            input("Sayfa yuklendiyse ENTER'a basin (tekrar deneyecek): ")
            time.sleep(2)
            tablo = ana_tablo_bul(driver)
            if not tablo:
                print("- Hala tablo bulunamadi. Script sonlandiriliyor.")
                return

        # 6) Başlıkları oku
        basliklar = tablo_basliklarini_oku(tablo)
        print(f"\n- Basliklar: {basliklar}")

        # 7) Tüm sayfalardaki satırları oku
        tum_satirlar = []
        sayfa_no = 1

        while True:
            print(f"\n- Sayfa {sayfa_no} okunuyor...")
            satirlar = tablo_satirlarini_oku(tablo)
            print(f"      {len(satirlar)} satır bulundu")
            tum_satirlar.extend(satirlar)

            if sayfalama_kontrol(driver):
                sayfa_no += 1
                tablo = ana_tablo_bul(driver)
                if not tablo:
                    break
            else:
                break

        print(f"\n- Toplam {len(tum_satirlar)} satir veri toplandi")

        # 8) Detay sayfalarını oku
        print("\n" + "="*60)
        print("   DETAY VERILERI VE BELGELER OKUNUYOR")
        print("="*60)
        
        driver.get(HEDEF_URL)
        time.sleep(5)

        # START LOOP
        islenecek = 0
        hata_sayisi = 0

        while islenecek < len(tum_satirlar):
            current_progress = f"[{islenecek + 1}/{len(tum_satirlar)}]"
            print(f"\n {current_progress} Isleniyor...")

            # --- Adim 1: Ana Sayfada Oldugumuzdan Emin Ol ---
            if HEDEF_URL not in driver.current_url:
                driver.get(HEDEF_URL)
                time.sleep(5)

            # --- Adim 2: Tabloyu ve Satiri Bul ---
            tablo = ana_tablo_bul(driver)
            if not tablo:
                print(f"      [!] Tablo bulunamadi, yeniden deneniyor...")
                driver.refresh()
                time.sleep(6)
                continue

            satirlar = tablo_satirlarini_oku(tablo)
            
            # Sayfalama kontrolü
            if islenecek >= len(satirlar):
                print(f"      [>] Sayfa sonuna gelindi, sonraki sayfa araniyor...")
                if sayfalama_kontrol(driver):
                    time.sleep(4)
                    continue
                else:
                    print(f"      [!] Baska sayfa kalmadi.")
                    break

            # --- Adim 3: Detay Butonuna Tikla ---
            satir_info = satirlar[islenecek]
            detay_butonu = satir_info["detay_butonu"]
            
            if not detay_butonu:
                print(f"      [!] Detay butonu bulunamadi, atlaniyor.")
                islenecek += 1
                continue

            try:
                ana_pencere = driver.current_window_handle
                onceki_pencereler = set(driver.window_handles)
                
                # Tiklama
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", detay_butonu)
                time.sleep(1)
                try:
                    detay_butonu.click()
                except:
                    driver.execute_script("arguments[0].click();", detay_butonu)
                
                time.sleep(5)
                
                # Yeni pencere kontrolu
                yeni_pencereler = set(driver.window_handles) - onceki_pencereler
                if yeni_pencereler:
                    driver.switch_to.window(yeni_pencereler.pop())
                    time.sleep(2)

                # --- Adim 4: Detaylari ve Belgeleri Oku ---
                detay = detay_sayfasini_oku(driver)
                tum_satirlar[islenecek]["detay_verileri"] = detay
                
                # Arastirma Adini bul (Klasor ismi icin)
                arastirma_adi = detay.get("Araştırmanın Adı", detay.get("Araştırma Adı", 
                                 detay.get("Baslik_Adi", "Bilinmiyor"))).strip()
                
                if arastirma_adi == "Bilinmiyor":
                    # Tablodan dene
                    try:
                        arastirma_adi = tum_satirlar[islenecek]["hucre_metinleri"][5]
                    except: pass
                
                # Başvuru No tespiti (Tablo verilerinden al - En güvenilir yer)
                basvuru_no = ""
                hucreler = tum_satirlar[islenecek].get("hucre_metinleri", [])
                
                # Sütun başlıkları ile hücreleri eşleştir
                tablo_datalari = {}
                if len(basliklar) <= len(hucreler):
                    tablo_datalari = dict(zip(basliklar, hucreler))
                
                # Tablo sütunlarından "No" içeren başlığı bulmaya çalış
                for k, v in tablo_datalari.items():
                    k_low = k.lower()
                    if "no" in k_low or "numara" in k_low:
                        val = str(v).strip()
                        if val and len(val) > 4:
                            basvuru_no = val
                            break
                            
                # Eğer tablodan gelmediyse detaylardan dene
                if not basvuru_no:
                    basvuru_no = str(detay.get("Basvuru Numarasi", detay.get("Başvuru Numarası", 
                                 detay.get("Başvuru No", "")))).strip()
                
                # Eğer hala boşsa hücrelerden "MEB" içeren bir şey ara
                if not basvuru_no:
                    for cell in hucreler:
                        temiz_cell = str(cell).strip()
                        if len(temiz_cell) > 5 and ("MEB" in temiz_cell or temiz_cell.count(".") > 1):
                            basvuru_no = temiz_cell
                            break
                
                if not basvuru_no: basvuru_no = "Bilinmiyor"
                
                # Klasör ismi için tam başvuru numarasını kullan
                klasor_etiketi = re.sub(r'[\\/:*?"<>|]', '_', basvuru_no)
                print(f"      -> {islenecek+1}. Kayit No: {basvuru_no}")

                # Belgeleri indir - Linkleri tekilleştir
                indirilecek_linkler = []
                gorulen_urller = set()
                for key, val in detay.items():
                    if isinstance(val, list):
                        for item in val:
                            if isinstance(item, dict) and "url" in item and item["url"]:
                                if item["url"] not in gorulen_urller:
                                    indirilecek_linkler.append(item)
                                    gorulen_urller.add(item["url"])

                # PARALEL INDIRME
                belge_sayisi = 0
                if indirilecek_linkler:
                    print(f"         * {len(indirilecek_linkler)} belge paralel indiriliyor...")
                    with ThreadPoolExecutor(max_workers=5) as executor:
                        future_to_item = {
                            executor.submit(belge_indir, item['url'], klasor_etiketi, item['text'], driver): item 
                            for item in indirilecek_linkler
                        }
                        for future in future_to_item:
                            item = future_to_item[future]
                            try:
                                yerel_yol = future.result()
                                if yerel_yol:
                                    item["local_path"] = yerel_yol
                                    belge_sayisi += 1
                            except Exception as e:
                                print(f"         [!] {item['text'][:20]} indirilemedi: {e}")
                    
                    if belge_sayisi > 0:
                        print(f"      [OK] {belge_sayisi} belge yerele kaydedildi.")
                
                # --- Adim 5: Geri Don ---
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(ana_pencere)
                else:
                    if HEDEF_URL not in driver.current_url:
                        driver.back()
                
                time.sleep(2)
                islenecek += 1
                hata_sayisi = 0
                
                # Her adimda yedekle (Kaza durumunda veri kaybolmasin)
                try:
                    json_export(basliklar, tum_satirlar, silent=True)
                    print(f"      [+] Veriler incremental olarak yedeklendi.")
                except: pass

            except Exception as e:
                print(f"      [HATA] Beklenmedik detay hatasi: {e}")
                hata_sayisi += 1
                if hata_sayisi > 3:
                    print("      [!!!] Cok fazla hata alindi, atlaniyor.")
                    islenecek += 1
                    hata_sayisi = 0
                driver.get(HEDEF_URL)
                time.sleep(5)

        # 9) Sonuçları yazdır
        toplam_detay = sum(1 for s in tum_satirlar if s.get("detay_verileri"))
        print("\n" + "=" * 60)
        print(f"   ISLEM TAMAMLANDI")
        print(f"   Toplam Satir      : {len(tum_satirlar)}")
        print(f"   Okunan Detay      : {toplam_detay}")
        print("=" * 60)

        # Excel ve JSON Yaz
        excel_dosya = excel_olustur(basliklar, tum_satirlar)
        json_dosya = json_export(basliklar, tum_satirlar, silent=True)

        print(f"\n   Excel: {excel_dosya}")
        print(f"   JSON : {json_dosya}")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nIslem kullanici tarafindan iptal edildi.")
    except Exception as e:
        print(f"\n\nHATA: {e}")
        traceback.print_exc()
    finally:
        print("\nTarayici acik birakildi.")


if __name__ == "__main__":
    main()
