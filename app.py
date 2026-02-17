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


def mebbis_json_yukle(json_path):
    """MEBBIS'ten export edilen JSON dosyasını okuyup veritabanına aktarır."""
    with open(json_path, "r", encoding="utf-8") as f:
        veriler = json.load(f)

    eklenen = 0
    atlanan = 0
    guncellenen = 0
    for kayit in veriler:
        detay = kayit.get("detay_verileri", {})
        basvuru_no = detay.get("Başvuru Numarası", "")
        if not basvuru_no:
            continue

        # Belge linklerini JSON'a çevir
        def belge_json(val):
            if isinstance(val, list):
                return json.dumps(val, ensure_ascii=False)
            return val if val else ""



        # Aynı başvuru zaten varsa → değerlendirici bilgisini güncelle
        mevcut = Basvuru.query.filter_by(basvuru_no=basvuru_no).first()
        if mevcut:
            guncellendi = False
            
            # Güncellenecek standart metin alanları
            metin_alanlari = {
                "basvuru_durumu": "Başvuru Durumu",
                "tc_kimlik": "TC Kimlik No",
                "ad_soyad": "Ad Soyad",
                "telefon": "Telefon",
                "eposta": "E-Posta",
                "adres": "Adres",
                "basvuru_sekli": "Başvuru Şekli",
                "basvuru_ulke": "Başvurunun Yapıldığı Ülke",
                "meslek": "Meslek",
                "calistigi_kurum": "Çalıştığı Kurum",
                "arastirma_adi": "Araştırmanın Adı",
                "egitim_teknoloji": "Eğitim Teknolojileri İle İlgili",
                "arastirma_niteligi": "Araştırmanın Niteliği",
                "akademik_basari": "Akademik Başarı Ölçme",
                "arastirma_konusu": "Araştırmanın Konusu ve İlişkili Konular",
                "anahtar_kelimeler": "Anahtar Kelimeler",
                "yazim_dili": "Araştırmanın Yazım Dili",
                "il_sayisi": "Uygulama Yapılacak İl Sayısı",
                "calisma_grubu": "Çalışma Grubu",
                "meb_teskilati": "Uygulama Yapılacak MEB Teşkilatı",
                "okul_kurum_sayisi": "Uygulama Okul/Kurum Sayısı",
                "ozel_bilgiler": "Özel Bilgiler",
                "uygulama_suresi": "Uygulama Süresi",
            }

            for db_alan, detay_key in metin_alanlari.items():
                yeni_val = detay.get(detay_key, "")
                if db_alan == "teskilat_turu":
                    yeni_val = _tekil_pipe(yeni_val)
                
                mevcut_val = getattr(mevcut, db_alan, "") or ""
                if yeni_val and yeni_val != mevcut_val:
                    setattr(mevcut, db_alan, yeni_val)
                    guncellendi = True

            # Belge linklerini güncelle
            belge_alanlari = {
                "belge_arastirma_proje": "Araştırma Proje Bilgileri (Link)",
                "belge_veri_toplama": "Veri Toplama Aracı (Link)",
                "belge_taahhutname": "Taahhütname (Link)",
                "belge_etik_kurul": "Etik Kurul Onay (Link)",
                "belge_gonullu_katilim": "Bilgilendirme ve Gönüllü Katılım Formu (Link)",
                "belge_veli_onam": "Veli Onam Formu (Link)",
                "belge_olcek_izni": "Ölçek Kullanım İzni (Link)",
                "diger_ekler": "Diğer Ekler",
            }
            for db_alan, detay_key in belge_alanlari.items():
                yeni_val_raw = detay.get(detay_key)
                yeni_deger = belge_json(yeni_val_raw)
                mevcut_deger = getattr(mevcut, db_alan, "") or ""
                
                # Eğer yeni veri gelmişse ve mevcutla aynı değilse güncelle (içerideki local_path farkları dahil)
                if yeni_deger and yeni_deger != mevcut_deger:
                    if "local_path" in yeni_deger:
                        print(f"      INFO: {detay_key} için yerel yol yüklendi.")
                    setattr(mevcut, db_alan, yeni_deger)
                    guncellendi = True
            if guncellendi:
                mevcut.guncelleme_tarihi = datetime.utcnow()
                guncellenen += 1
            else:
                atlanan += 1
            continue

        basvuru = Basvuru(
            basvuru_no=basvuru_no,
            basvuru_tarihi=detay.get("Başvuru Tarihi", ""),
            basvuru_durumu=detay.get("Başvuru Durumu", ""),
            tc_kimlik=detay.get("TC Kimlik No", ""),
            ad_soyad=detay.get("Ad Soyad", ""),
            telefon=detay.get("Telefon", ""),
            eposta=detay.get("E-Posta", ""),
            adres=detay.get("Adres", ""),
            basvuru_sekli=detay.get("Başvuru Şekli", ""),
            basvuru_ulke=detay.get("Başvurunun Yapıldığı Ülke", ""),
            meslek=detay.get("Meslek", ""),
            calistigi_kurum=detay.get("Çalıştığı Kurum", ""),
            arastirma_adi=detay.get("Araştırmanın Adı", ""),
            egitim_teknoloji=detay.get("Eğitim Teknolojileri İle İlgili", ""),
            arastirma_niteligi=detay.get("Araştırmanın Niteliği", ""),
            akademik_basari=detay.get("Akademik Başarı Ölçme", ""),
            arastirma_konusu=detay.get("Araştırmanın Konusu ve İlişkili Konular", ""),
            anahtar_kelimeler=detay.get("Anahtar Kelimeler", ""),
            yazim_dili=detay.get("Araştırmanın Yazım Dili", ""),
            il_sayisi=detay.get("Uygulama Yapılacak İl Sayısı", ""),
            calisma_grubu=detay.get("Çalışma Grubu", ""),
            teskilat_turu=_tekil_pipe(detay.get("Teşkilat Türü", "")),
            meb_teskilati=detay.get("Uygulama Yapılacak MEB Teşkilatı", ""),
            okul_kurum_sayisi=detay.get("Uygulama Okul/Kurum Sayısı", ""),
            ozel_bilgiler=detay.get("Özel Bilgiler", ""),
            uygulama_suresi=detay.get("Uygulama Süresi", ""),
            belge_arastirma_proje=belge_json(detay.get("Araştırma Proje Bilgileri (Link)")),
            belge_veri_toplama=belge_json(detay.get("Veri Toplama Aracı (Link)")),
            belge_taahhutname=belge_json(detay.get("Taahhütname (Link)")),
            belge_etik_kurul=belge_json(detay.get("Etik Kurul Onay (Link)")),
            belge_gonullu_katilim=belge_json(detay.get("Bilgilendirme ve Gönüllü Katılım Formu (Link)")),
            belge_veli_onam=belge_json(detay.get("Veli Onam Formu (Link)")),
            belge_olcek_izni=belge_json(detay.get("Ölçek Kullanım İzni (Link)")),
            diger_ekler=belge_json(detay.get("Diğer Ekler")),
        )
        db.session.add(basvuru)
        db.session.flush()  # ID almak için

        # Ön kontrol maddelerini oluştur
        for madde in ON_KONTROL_MADDELERI:
            ok = OnKontrol(
                basvuru_id=basvuru.id,
                sira=madde["sira"],
                madde_adi=madde["ad"],
                durum="",
                aciklama=""
            )
            db.session.add(ok)

        # Kriterleri oluştur
        for kriter in KRITERLER:
            kd = KriterDegerlendirme(
                basvuru_id=basvuru.id,
                kriter_no=kriter["no"],
                sonuc="",
                aciklama=""
            )
            db.session.add(kd)

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
