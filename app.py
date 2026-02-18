# -*- coding: utf-8 -*-
"""
MEB Araştırma İzni Değerlendirme Platformu
==========================================
Flask tabanlı web uygulaması.
"""
import json
import os
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
from models import db, Basvuru, OnKontrol, KriterDegerlendirme, BasvuruDegerlendirici, ON_KONTROL_MADDELERI, KRITERLER

# ─── Uygulama Ayarları ───────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "degerlendirme.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = "meb-arastirma-izni-2026"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()


# ─── DEĞERLENDİRİCİ LİSTESİ ─────────────────────────────────────────────────
DEGERLENDIRICILER = [
    "FATİH DEVECİ",
    "MUHAMMET BAHADIR ŞAHİN",
    "ÇİĞDEM HODUL",
    "SEMA AKBAŞ",
]


# ─── YARDIMCI FONKSİYONLAR ───────────────────────────────────────────────────

def _tekil_pipe(deger):
    """Pipe ile ayrılmış tekrarlayan değerleri tekilleştirir.
    Örnek: 'Okul / Kurum | Okul / Kurum | Okul / Kurum' -> 'Okul / Kurum'
    Farklı değerler varsa alt alta (newline) birleştirir.
    """
    if not deger:
        return ""
    parcalar = [p.strip() for p in deger.split("|") if p.strip()]
    # Sırayı koruyarak tekilleri al
    gorulen = []
    for p in parcalar:
        if p not in gorulen:
            gorulen.append(p)
    return "\n".join(gorulen)


def _normalize_key(key):
    """Büyük harf ve Türkçe karakter dönüşümü yaparak temizler."""
    if not key:
        return ""
    # Türkçe karakterleri ASCII karşılıklarına çevir
    key = key.replace("İ", "I").replace("ı", "I").replace("Ğ", "G").replace("ğ", "G")\
             .replace("Ü", "U").replace("ü", "U").replace("Ş", "S").replace("ş", "S")\
             .replace("Ö", "O").replace("ö", "O").replace("Ç", "C").replace("ç", "C")
    return key.upper().strip()


def _get_val_robust(kayit, detay_keys, tablo_keys=None):
    """Veriyi önce detaydan, sonra tablodan (fuzzy match) dener."""
    detay = kayit.get("detay_verileri", {})
    tablo = kayit.get("tablo_verileri", {})

    # 1. Detay verilerinde ara
    if isinstance(detay_keys, str):
        detay_keys = [detay_keys]
    
    for dk in detay_keys:
        val = detay.get(dk)
        if val is None:
            val = detay.get(dk + " (Link)")
        
        # Eğer veri string değilse (örn: Link listesi)
        if isinstance(val, list) and val and isinstance(val[0], dict):
            # Link listesinden anlamlı veri çıkarmaya çalış
            normalized_key = _normalize_key(dk)
            
            # AD SOYAD Çıkarımı
            # print(f"DEBUG: Key: {normalized_key}")
            if "AD" in normalized_key and "SOYAD" in normalized_key:
                print(f"DEBUG: Entering Ad Soyad block for {normalized_key}")  
                for item in val:
                    text = item.get("text", "")
                    # "Ad Soyad - Belge Adı" formatını yakala
                    if " - " in text:
                        candidate = text.split(" - ")[0].strip()
                        # "Safa Demir" gibi en az 2 kelime ve makul uzunlukta
                        if " " in candidate and len(candidate) > 5 and len(candidate) < 50:
                            return candidate
            
            # TELEFON Çıkarımı
            if "TELEFON" in normalized_key:
                # Link metinlerinde telefon ara (Nadir durum ama kontrol edelim)
                import re
                phone_pattern = re.compile(r'(5\d{2}\s*\d{3}\s*\d{2}\s*\d{2})')
                for item in val:
                    text = item.get("text", "")
                    match = phone_pattern.search(text)
                    if match:
                        return match.group(0)

            # E-POSTA Çıkarımı
            if "POSTA" in normalized_key:
                for item in val:
                    text = item.get("text", "")
                    if "@" in text and "." in text:
                        return text.strip()

            # Link değilse ve düz liste gelmişse (nadir)
            continue
            
        # Normal string değer
        if val and not isinstance(val, (dict, list)): 
            return str(val).strip()
    
    # Kapsamlı Arama (Deep Search) - Sadece Ad Soyad için
    # Eğer yukarıdaki standart arama sonuç vermediyse ve "AD SOYAD" arıyorsak
    is_ad_soyad = False
    
    # detay_keys is ALREADY a list here due to earlier conversion
    for k in detay_keys:
         nk = _normalize_key(k)
         if "AD" in nk and "SOYAD" in nk:
             is_ad_soyad = True
             break
    
    if is_ad_soyad:
        # Detay verilerindeki TÜM Link alanlarını tara
        for key, val in detay.items():
            if isinstance(val, list) and val and isinstance(val[0], dict):
                 for item in val:
                    text = item.get("text", "")
                    if " - " in text:
                        candidate = text.split(" - ")[0].strip()
                        # İsim doğrulama (en az 2 kelime, makul uzunluk, sayı içermeyen)
                        if " " in candidate and len(candidate) > 5 and len(candidate) < 50 and not any(char.isdigit() for char in candidate):
                            return candidate

    # 2. Tablo verilerinde ara (Key normalizasyonu ile)
    if tablo_keys:
        if isinstance(tablo_keys, str):
            tablo_keys = [tablo_keys]
        
        # Tablo anahtarlarını normalize et
        norm_tablo = {_normalize_key(k): v for k, v in tablo.items()}
        
        for tk in tablo_keys:
            norm_tk = _normalize_key(tk)
            # Tam eşleşme ara
            val = norm_tablo.get(norm_tk)
            if val:
                return str(val).strip()
            
            # Kısmi eşleşme ara (örn: "BAŞVURU TARİHİ" -> "BAŞVURU\nTARİHİ")
            for nk, nv in norm_tablo.items():
                if norm_tk in nk:
                    return str(nv).strip()

    return ""


def mebbis_json_yukle(json_path):
    """MEBBIS'ten export edilen JSON dosyasını okuyup veritabanına aktarır."""
    with open(json_path, "r", encoding="utf-8") as f:
        veriler = json.load(f)

    eklenen = 0
    atlanan = 0
    guncellenen = 0
    yeni_idler = []

    for kayit in veriler:
        detay = kayit.get("detay_verileri", {})
        
        # Başvuru Numarasını Bul (Önce detay, sonra tablo)
        basvuru_no = _get_val_robust(kayit, "Başvuru Numarası", ["BAŞVURU NO", "BAŞVURU NUMARASI"])
        
        if not basvuru_no or basvuru_no == "Bilinmiyor":
            # Tablo verilerinden "MEB" ile başlayan bir şey var mı bak
            tablo = kayit.get("tablo_verileri", {})
            for v in tablo.values():
                if isinstance(v, str) and "MEB" in v and len(v) > 10:
                    basvuru_no = v
                    break
        
        if not basvuru_no:
            # print("Uyarı: Başvuru numarası bulunamadı, atlanıyor.")
            continue

        # Belge linklerini JSON'a çevir
        def belge_json(val):
            if isinstance(val, list):
                return json.dumps(val, ensure_ascii=False)
            return val if val else ""

        # Mevcut kaydı kontrol et
        mevcut = Basvuru.query.filter_by(basvuru_no=basvuru_no).first()
        
        # Veri setini hazırla
        yeni_veri = {
            "basvuru_tarihi": _get_val_robust(kayit, "Başvuru Tarihi", ["BAŞVURU TARİHİ", "TARIH"]),
            "basvuru_durumu": _get_val_robust(kayit, "Başvuru Durumu", "BAŞVURU DURUMU"),
            "tc_kimlik": _get_val_robust(kayit, "TC Kimlik No"),
            "ad_soyad": _get_val_robust(kayit, "Ad Soyad"),
            "telefon": _get_val_robust(kayit, "Telefon"),
            "eposta": _get_val_robust(kayit, "E-Posta"),
            "adres": _get_val_robust(kayit, "Adres"),
            "basvuru_sekli": _get_val_robust(kayit, "Başvuru Şekli"),
            "basvuru_ulke": _get_val_robust(kayit, "Başvurunun Yapıldığı Ülke"),
            "meslek": _get_val_robust(kayit, "Meslek"),
            "calistigi_kurum": _get_val_robust(kayit, "Çalıştığı Kurum"),
            "arastirma_adi": _get_val_robust(kayit, "Araştırmanın Adı", ["ARAŞTIRMANIN ADI", "PROJE ADI"]),
            "egitim_teknoloji": _get_val_robust(kayit, "Eğitim Teknolojileri İle İlgili"),
            "arastirma_niteligi": _get_val_robust(kayit, "Araştırmanın Niteliği", "NITELIĞI"),
            "akademik_basari": _get_val_robust(kayit, "Akademik Başarı Ölçme"),
            "arastirma_konusu": _get_val_robust(kayit, "Araştırmanın Konusu ve İlişkili Konular"),
            "anahtar_kelimeler": _get_val_robust(kayit, "Anahtar Kelimeler"),
            "yazim_dili": _get_val_robust(kayit, "Araştırmanın Yazım Dili"),
            "il_sayisi": _get_val_robust(kayit, "Uygulama Yapılacak İl Sayısı"),
            "calisma_grubu": _get_val_robust(kayit, "Çalışma Grubu"),
            "teskilat_turu": _tekil_pipe(_get_val_robust(kayit, "Teşkilat Türü", "UYGULAMA YAPILACAK KURUM TÜRÜ")),
            "meb_teskilati": _get_val_robust(kayit, "Uygulama Yapılacak MEB Teşkilatı"),
            "okul_kurum_sayisi": _get_val_robust(kayit, "Uygulama Okul/Kurum Sayısı"),
            "ozel_bilgiler": _get_val_robust(kayit, "Özel Bilgiler"),
            "uygulama_suresi": _get_val_robust(kayit, "Uygulama Süresi", "SÜRE"),
        }

        # ───────────────────────────────────────────────────────────────────────────
        # BELGE AYRIŞTIRMA VE EŞLEŞTİRME (Refactored)
        # ───────────────────────────────────────────────────────────────────────────
        # Hedef: Tüm benzersiz belgeleri bul, kategorilere dağıt, kalanları "Diğer"e at.
        
        tum_belgeler = []
        gordugum_urller = set()

        # 1. Kayıt içindeki TÜM linkli alanları tara ve benzersizleri topla
        def _belgeleri_topla(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict) and "url" in item and "text" in item:
                                url = item["url"].strip()
                                text = item["text"].strip()
                                
                                # Text temizliği
                                clean_text = text
                                # Hem kısa (-) hem uzun (–) tireyi handle et
                                separator = None
                                if " - " in text: separator = " - "
                                elif " – " in text: separator = " – "
                                
                                if separator:
                                    parts = text.split(separator, 1)
                                    if len(parts) > 1:
                                        clean_text = parts[1].strip()
                                
                                # Eğer temizleme sonucu boş kaldıysa (veya ayırıcı yoksa) orijinali koru
                                if not clean_text:
                                    clean_text = text
                                
                                # Uzantı temizliği (örn: .pdf, .docx sil)
                                base_text = str(clean_text)
                                lower_text = base_text.lower()
                                for ext in [".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png"]:
                                    if lower_text.endswith(ext):
                                        base_text = base_text[:-len(ext)].strip()
                                        break
                                
                                # Filtreli: "Ana Başvuru" vb. gereksiz dosyaları atla
                                id_text = _normalize_key(base_text)
                                if id_text in ["ANA BASVURU", "ANA BAŞVURU", "BASVURU FORMU"]:
                                    continue

                                item["clean_text"] = base_text # Görüntülenen temiz isim
                                
                                # Benzersizlik İçin Normalize Edilmiş Kimlikler
                                # URL'deki asıl dosya ID'sini çek (download/ sonrasındaki benzersiz kod)
                                if "/download/" in url:
                                    id_url = url.split("/download/")[1].split("?")[0]
                                else:
                                    id_url = url.split("?")[0].replace("http://", "").replace("https://", "").replace("\\", "/").rstrip("/")

                                if id_url not in gordugum_urller:
                                    gordugum_urller.add(id_url)
                                    tum_belgeler.append(item)
                    elif isinstance(v, dict):
                        _belgeleri_topla(v)
        
        _belgeleri_topla(detay)

        # 2. Kategorilere göre dağıtılacak kutular
        dagitim = {
            "belge_arastirma_proje": [],
            "belge_veri_toplama": [],
            "belge_taahhutname": [],
            "belge_etik_kurul": [],
            "belge_gonullu_katilim": [],
            "belge_veli_onam": [],
            "belge_olcek_izni": [],
            "belge_enstitu_karari": [],
            "diger_ekler": []
        }

        from collections import OrderedDict
        # 3. Anahtar kelimeler (MEBBİS Standart İsimleri ve Kısaltmalar)
        # Öncelik sırası önemlidir (Yukarıdaki kategoriler önce kontrol edilir)
        kelimeler = OrderedDict([
            ("belge_taahhutname", ["TAAHHUTNAME"]),
            ("belge_etik_kurul", ["ETIK KURUL", "ONAY BELGESI"]),
            ("belge_gonullu_katilim", ["GONULLU KATILIM", "BILGILENDIRME", "AYRINTILI BILGILENDIRME"]),
            ("belge_veli_onam", ["VELI ONAM", "VELI IZIN"]),
            ("belge_olcek_izni", ["OLCEK KULLANIM", "ALANYAZIN", "OLCEGI IZNI", "OLCEK IZNI", "KULLANIMA ILISKIN IZIN"]),
            ("belge_enstitu_karari", ["ENSTITU", "YONETIM KURULU", "YK KARARI"]),
            ("belge_arastirma_proje", ["ARASTIRMA PROJE", "PROJE BILGILERI", "TEZ ONERISI", "OZGECMIS", "CV"]),
            ("belge_veri_toplama", ["VERI TOPLAMA", "ANKET", "MULAKAT", "GORUSME", "SORU", "VTA", "OLCEK"])
        ])

        # 4. Her bir belgeyi uygun kutuya at (Sırayla, ilk uyan alır)
        for belge in tum_belgeler:
            txt_norm = _normalize_key(belge["text"]) # Tüm text üzerinden ara
            esanlesti = False
            
            for db_field, keys in kelimeler.items():
                if any(k in txt_norm for k in keys):
                    dagitim[db_field].append(belge)
                    esanlesti = True
                    break # Bir kategoriye girdiyse diğerlerine bakma
            
            if not esanlesti:
                # Hiçbir kategoriye uymadıysa Araştırma/Proje Bilgileri'ne ekle (Diğer Ekler başlığı kaldırıldı)
                dagitim["belge_arastirma_proje"].append(belge)

        # 5. DB Formatına Çevir (List -> JSON String)
        # 5. DB Kaydını Belirle (Güncelleme mi Yeni mi?)
        target_obj = mevcut
        is_new = False
        
        if not target_obj:
            target_obj = Basvuru(basvuru_no=basvuru_no)
            is_new = True
            db.session.add(target_obj)
        
        # 6. Verileri Uygula (Metin Alanları)
        is_changed = False
        
        # MEBBIS Durumunu İç Duruma Eşle
        mebbis_durum = yeni_veri.get("basvuru_durumu", "").upper()
        if "ONAY" in mebbis_durum:
            yeni_veri["degerlendirme_durumu"] = "devam"
        elif "TAMAM" in mebbis_durum or "SONUÇ" in mebbis_durum or "KABUL" in mebbis_durum:
            yeni_veri["degerlendirme_durumu"] = "tamamlandi"
        else:
            yeni_veri["degerlendirme_durumu"] = "bekliyor"

        for db_field, val in yeni_veri.items():
            old_val = getattr(target_obj, db_field, "") or ""
            if val and str(val) != str(old_val):
                setattr(target_obj, db_field, val)
                is_changed = True

        # 7. Belgeleri Uygula (JSON String)
        def liste_to_json(liste):
            if not liste: return None
            return json.dumps(liste, ensure_ascii=False)

        for db_field, liste in dagitim.items():
            new_val_json = liste_to_json(liste)
            old_val_json = getattr(target_obj, db_field, "") or ""
            if new_val_json != old_val_json:
                setattr(target_obj, db_field, new_val_json)
                is_changed = True
            
        # 8. Kaydet ve Sayaçları Güncelle
        if is_new:
            db.session.flush()
            yeni_idler.append(target_obj.id)
            # Alt tabloları oluştur
            for madde in ON_KONTROL_MADDELERI:
                db.session.add(OnKontrol(basvuru_id=target_obj.id, sira=madde["sira"], madde_adi=madde["ad"]))
            for kriter in KRITERLER:
                db.session.add(KriterDegerlendirme(basvuru_id=target_obj.id, kriter_no=kriter["no"]))
            eklenen += 1
        elif is_changed:
            target_obj.guncelleme_tarihi = datetime.utcnow()
            guncellenen += 1
        else:
            atlanan += 1

    db.session.commit()
    return eklenen, atlanan, guncellenen, yeni_idler


def belge_linklerini_parse(belge_str):
    """Belge string'ini link listesine çevirir."""
    if not belge_str:
        return []
    try:
        parsed = json.loads(belge_str)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    # Eski format: düz URL
    if belge_str.startswith("http"):
        return [{"text": "Belge", "url": belge_str}]
    return []


# ─── ROTALAR ─────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    """Ana sayfa: Başvuru listesi."""
    basvurular = Basvuru.query.order_by(Basvuru.olusturma_tarihi.desc()).all()

    # Yeni başvuru tespiti (Session'dan gelenler)
    # Kullanıcı isteği: Sadece son import işleminde eklenenler "Yeni" olarak işaretlensin.
    yeni_idler_list = session.get("yeni_idler")
    if yeni_idler_list:
        yeni_idler = set(yeni_idler_list)
    else:
        yeni_idler = set()

    # Her değerlendiricinin iş yükünü hesapla
    is_yuku = {}
    for d in DEGERLENDIRICILER:
        is_yuku[d] = BasvuruDegerlendirici.query.filter_by(degerlendirici_adi=d).count()

    # Değerlendirici paneli verileri
    deg_panel = []
    for d in DEGERLENDIRICILER:
        atamalar = BasvuruDegerlendirici.query.filter_by(degerlendirici_adi=d).all()
        gorevler = []
        toplam = len(atamalar)
        bekliyor = devam = tamamlandi = 0
        for atama in atamalar:
            b = Basvuru.query.get(atama.basvuru_id)
            if b:
                durum = b.degerlendirme_durumu or "bekliyor"
                if durum == "bekliyor":
                    bekliyor += 1
                elif durum == "devam":
                    devam += 1
                elif durum == "tamamlandi":
                    tamamlandi += 1
                gorevler.append({
                    "id": b.id,
                    "basvuru_no": b.basvuru_no,
                    "ad_soyad": b.ad_soyad,
                    "durum": durum,
                })
        deg_panel.append({
            "ad": d,
            "toplam": toplam,
            "bekliyor": bekliyor,
            "devam": devam,
            "tamamlandi": tamamlandi,
            "gorevler": gorevler,
        })

    return render_template(
        "dashboard.html",
        basvurular=basvurular,
        is_yuku=is_yuku,
        degerlendiriciler=DEGERLENDIRICILER,
        yeni_idler=yeni_idler,
        deg_panel=deg_panel,
    )


@app.route("/basvuru/<int:id>")
def degerlendirme(id):
    """Değerlendirme formu sayfası."""
    basvuru = Basvuru.query.get_or_404(id)
    on_kontroller = OnKontrol.query.filter_by(basvuru_id=id).order_by(OnKontrol.sira).all()
    kriterler_db = KriterDegerlendirme.query.filter_by(basvuru_id=id).order_by(KriterDegerlendirme.kriter_no).all()

    # Kriter sabitlerini eşleştir
    kriter_map = {k.kriter_no: k for k in kriterler_db}
    kriterler = []
    for ks in KRITERLER:
        db_k = kriter_map.get(ks["no"])
        kriterler.append({
            "no": ks["no"],
            "metin": ks["metin"],
            "sonuc": db_k.sonuc if db_k else "",
            "aciklama": db_k.aciklama if db_k else "",
        })

    # Belge linkleri
    belgeler = {
        "arastirma_proje": belge_linklerini_parse(basvuru.belge_arastirma_proje),
        "veri_toplama": belge_linklerini_parse(basvuru.belge_veri_toplama),
        "taahhutname": belge_linklerini_parse(basvuru.belge_taahhutname),
        "etik_kurul": belge_linklerini_parse(basvuru.belge_etik_kurul),
        "gonullu_katilim": belge_linklerini_parse(basvuru.belge_gonullu_katilim),
        "veli_onam": belge_linklerini_parse(basvuru.belge_veli_onam),
        "olcek_izni": belge_linklerini_parse(basvuru.belge_olcek_izni),
        "enstitu_karari": belge_linklerini_parse(basvuru.belge_enstitu_karari),
        "diger_ekler": belge_linklerini_parse(basvuru.diger_ekler),
    }

    # Atanmış değerlendiriciler
    atanmis = [bd.degerlendirici_adi for bd in basvuru.degerlendiriciler]

    # Her değerlendiricinin iş yükünü hesapla
    is_yuku = {}
    for d in DEGERLENDIRICILER:
        is_yuku[d] = BasvuruDegerlendirici.query.filter_by(degerlendirici_adi=d).count()

    return render_template(
        "degerlendirme.html",
        basvuru=basvuru,
        on_kontroller=on_kontroller,
        kriterler=kriterler,
        belgeler=belgeler,
        degerlendiriciler=DEGERLENDIRICILER,
        on_kontrol_maddeleri=ON_KONTROL_MADDELERI,
        atanmis_degerlendiriciler=atanmis,
        is_yuku=is_yuku,
    )


@app.route("/basvuru/<int:id>/kaydet", methods=["POST"])
def degerlendirme_kaydet(id):
    """Değerlendirme formunu kaydet."""
    basvuru = Basvuru.query.get_or_404(id)

    # Değerlendiricileri kaydet (checkbox'lardan)
    secilen = request.form.getlist("degerlendiriciler")
    # Mevcut atamaları temizle
    BasvuruDegerlendirici.query.filter_by(basvuru_id=id).delete()
    for deg_adi in secilen[:2]:  # En fazla 2
        bd = BasvuruDegerlendirici(basvuru_id=id, degerlendirici_adi=deg_adi)
        db.session.add(bd)

    # Ön kontrolleri kaydet
    for madde in ON_KONTROL_MADDELERI:
        sira = madde["sira"]
        ok = OnKontrol.query.filter_by(basvuru_id=id, sira=sira).first()
        if ok:
            ok.durum = request.form.get(f"on_kontrol_durum_{sira}", "")
            ok.aciklama = request.form.get(f"on_kontrol_aciklama_{sira}", "")

    # Kriterleri kaydet
    for ks in KRITERLER:
        no = ks["no"]
        kd = KriterDegerlendirme.query.filter_by(basvuru_id=id, kriter_no=no).first()
        if kd:
            kd.sonuc = request.form.get(f"kriter_sonuc_{no}", "")
            kd.aciklama = request.form.get(f"kriter_aciklama_{no}", "")

    # Değerlendirme durumunu güncelle
    tum_kriterler = KriterDegerlendirme.query.filter_by(basvuru_id=id).all()
    dolu = sum(1 for k in tum_kriterler if k.sonuc)
    if dolu == 0:
        basvuru.degerlendirme_durumu = "bekliyor"
    elif dolu == len(KRITERLER):
        basvuru.degerlendirme_durumu = "tamamlandi"
    else:
        basvuru.degerlendirme_durumu = "devam"

    basvuru.guncelleme_tarihi = datetime.utcnow()
    db.session.commit()

    flash("Değerlendirme başarıyla kaydedildi!", "success")
    return redirect(url_for("degerlendirme", id=id))


@app.route("/mebbis-aktar", methods=["POST"])
def mebbis_aktar():
    """MEBBIS JSON dosyasını yükleyip veritabanına aktarır."""
    if "json_dosya" not in request.files:
        flash("Lütfen bir JSON dosyası seçin.", "error")
        return redirect(url_for("dashboard"))

    dosya = request.files["json_dosya"]
    if dosya.filename == "":
        flash("Dosya seçilmedi.", "error")
        return redirect(url_for("dashboard"))

    # Geçici dosyayı kaydet
    gecici_yol = os.path.join(BASE_DIR, "temp_mebbis.json")
    dosya.save(gecici_yol)

    try:
        eklenen, atlanan, guncellenen, yeni_idler = mebbis_json_yukle(gecici_yol)
        
        # Yeni eklenenleri session'a kaydet (Dashboard'da göstermek için)
        session["yeni_idler"] = yeni_idler
        
        mesajlar = []
        if eklenen > 0:
            mesajlar.append(f"{eklenen} yeni başvuru aktarıldı")
        if guncellenen > 0:
            mesajlar.append(f"{guncellenen} başvuru güncellendi")
        if atlanan > 0:
            mesajlar.append(f"{atlanan} başvuru değişmedi")
        if mesajlar:
            flash(", ".join(mesajlar) + ".", "success" if eklenen > 0 or guncellenen > 0 else "info")
        else:
            flash("Dosyada geçerli başvuru bulunamadı.", "warning")
    except Exception as e:
        flash(f"Aktarma hatası: {str(e)}", "error")
    finally:
        if os.path.exists(gecici_yol):
            os.remove(gecici_yol)

    return redirect(url_for("dashboard"))


@app.route("/basvuru/<int:id>/sil", methods=["POST"])
def basvuru_sil(id):
    """Başvuruyu siler."""
    basvuru = Basvuru.query.get_or_404(id)
    db.session.delete(basvuru)
    db.session.commit()
    flash("Başvuru silindi.", "info")
    return redirect(url_for("dashboard"))


@app.route("/belge-goster/<path:filename>")
def serve_doc(filename):
    """Yerel belgeleri inline olarak sunar."""
    # Başlık parametresini al (indirilecek olursa kullanılacak isim)
    display_name = request.args.get("title", "belge")
    # Dosya sistemindeki ismi temizle
    clean_filename = filename.replace("static/belgeler/", "").replace("static\\belgeler\\", "")
    directory = os.path.join(BASE_DIR, "static", "belgeler")
    full_path = os.path.join(directory, clean_filename)

    if not os.path.exists(full_path):
        return f"Dosya bulunamadı: {clean_filename}", 404

    from flask import make_response
    with open(full_path, 'rb') as f:
        content = f.read()

    response = make_response(content)
    response.headers["Content-Type"] = "application/pdf"
    # UTF-8 karakter desteği için filename* kullanımı
    from urllib.parse import quote
    safe_name = quote(display_name)
    response.headers["Content-Disposition"] = f"inline; filename=\"{safe_name}.pdf\"; filename*=UTF-8''{safe_name}.pdf"
    # Frame kısıtlamalarını kaldır
    response.headers.pop("X-Frame-Options", None)
    return response


@app.route("/proxy-belge")
def proxy_belge():
    """Dış MEBBİS belgelerini inline olarak sunar."""
    url = request.args.get("url")
    display_name = request.args.get("title", "belge")
    
    if not url:
        return "URL eksik", 400
    if "meb.gov.tr" not in url:
        return "Geçersiz kaynak", 403

    try:
        import requests
        from flask import make_response
        r = requests.get(url, timeout=15)
        
        response = make_response(r.content)
        response.headers["Content-Type"] = "application/pdf"
        
        from urllib.parse import quote
        safe_name = quote(display_name)
        response.headers["Content-Disposition"] = f"inline; filename=\"{safe_name}.pdf\"; filename*=UTF-8''{safe_name}.pdf"
        # X-Frame-Options KESİNLİKLE kaldırılmalı yoksa iframe açılmaz
        response.headers.pop("X-Frame-Options", None)
        return response
    except Exception as e:
        return f"Hata: {str(e)}", 500


# ─── TEMPLATE FİLTRELERİ ─────────────────────────────────────────────────────

@app.template_filter("durum_renk")
def durum_renk_filter(durum):
    renk_map = {
        "bekliyor": "warning",
        "devam": "info",
        "tamamlandi": "success",
    }
    return renk_map.get(durum, "secondary")


@app.template_filter("durum_ikon")
def durum_ikon_filter(durum):
    ikon_map = {
        "bekliyor": "bi-hourglass-split",
        "devam": "bi-pencil-square",
        "tamamlandi": "bi-check-circle-fill",
    }
    return ikon_map.get(durum, "bi-question-circle")


@app.template_filter("durum_metin")
def durum_metin_filter(durum):
    metin_map = {
        "bekliyor": "Bekliyor",
        "devam": "Devam Ediyor",
        "tamamlandi": "Tamamlandı",
    }
    return metin_map.get(durum, "Bilinmiyor")


# ─── ANA ÇALIŞTIRMA ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)
