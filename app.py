# -*- coding: utf-8 -*-
"""
MEB Araştırma İzni Değerlendirme Platformu
==========================================
Flask tabanlı web uygulaması.
"""
import json
import os
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
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
    # Basitçe \n ve boşlukları temizle, büyük harfe çevir
    return key.replace("\n", " ").replace("İ", "I").upper().strip()


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

        # Belge linkleri (Bunlar zaten Link formatında geliyor, direkt detaydan alıyoruz)
        belge_keys = {
            "belge_arastirma_proje": "Araştırma Proje Bilgileri (Link)",
            "belge_veri_toplama": "Veri Toplama Aracı (Link)",
            "belge_taahhutname": "Taahhütname (Link)",
            "belge_etik_kurul": "Etik Kurul Onay (Link)",
            "belge_gonullu_katilim": "Bilgilendirme ve Gönüllü Katılım Formu (Link)",
            "belge_veli_onam": "Veli Onam Formu (Link)",
            "belge_olcek_izni": "Ölçek Kullanım İzni (Link)",
            "diger_ekler": "Diğer Ekler",
        }

        if basvuru_no == "MEB.TT.2025.044260.02":
             # Bu kaydın detay verileri boş olduğu için Ad Soyad'ı manuel set etme şansımız yok
             # Ancak tablo verileri ile en azından kaydı oluşturabiliriz.
             pass

        # MEBBIS Durumunu İç Duruma Eşle
        mebbis_durum = yeni_veri.get("basvuru_durumu", "").upper()
        if "ONAY" in mebbis_durum:
            yeni_veri["degerlendirme_durumu"] = "devam"
        elif "TAMAM" in mebbis_durum or "SONUÇ" in mebbis_durum or "KABUL" in mebbis_durum:
            yeni_veri["degerlendirme_durumu"] = "tamamlandi"
        else:
            yeni_veri["degerlendirme_durumu"] = "bekliyor"

        if mevcut:
            is_changed = False
            # Metin alanlarını güncelle
            for db_field, val in yeni_veri.items():
                old_val = getattr(mevcut, db_field, "") or ""
                if val and val != old_val:
                    setattr(mevcut, db_field, val)
                    is_changed = True
            
            # Belge alanlarını güncelle
            for db_field, json_key in belge_keys.items():
                new_val_raw = detay.get(json_key)
                if new_val_raw:
                    new_val_json = belge_json(new_val_raw)
                    old_val_json = getattr(mevcut, db_field, "") or ""
                    if new_val_json and new_val_json != old_val_json:
                        setattr(mevcut, db_field, new_val_json)
                        is_changed = True
            
            if is_changed:
                mevcut.guncelleme_tarihi = datetime.utcnow()
                guncellenen += 1
            else:
                atlanan += 1
        else:
            # Yeni Başvuru
            basvuru = Basvuru(basvuru_no=basvuru_no, **yeni_veri)
            
            # Belgeleri ekle
            for db_field, json_key in belge_keys.items():
                setattr(basvuru, db_field, belge_json(detay.get(json_key)))
            
            db.session.add(basvuru)
            db.session.flush()

            # Alt tabloları oluştur
            for madde in ON_KONTROL_MADDELERI:
                db.session.add(OnKontrol(basvuru_id=basvuru.id, sira=madde["sira"], madde_adi=madde["ad"]))
            
            for kriter in KRITERLER:
                db.session.add(KriterDegerlendirme(basvuru_id=basvuru.id, kriter_no=kriter["no"]))

            eklenen += 1

    db.session.commit()
    return eklenen, atlanan, guncellenen


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

    # Yeni başvuru tespiti (son 24 saat içinde eklenenler)
    yeni_esik = datetime.utcnow() - timedelta(hours=24)
    yeni_idler = {b.id for b in basvurular if b.olusturma_tarihi and b.olusturma_tarihi >= yeni_esik}

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
        eklenen, atlanan, guncellenen = mebbis_json_yukle(gecici_yol)
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
    """Belgeleri tarayıcıda açılacak (inline) şekilde sunar."""
    # Eğer filename başında 'static/belgeler/' varsa temizle
    clean_filename = filename.replace("static/belgeler/", "").replace("static\\belgeler\\", "")
    
    # Dosya yolunu oluştur
    directory = os.path.join(BASE_DIR, "static", "belgeler")
    
    return send_from_directory(
        directory,
        clean_filename,
        as_attachment=False
    )


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
