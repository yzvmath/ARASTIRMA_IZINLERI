# -*- coding: utf-8 -*-
"""
Veritabanı Modelleri
====================
MEB Araştırma İzni Değerlendirme Platformu için SQLAlchemy modelleri
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Basvuru(db.Model):
    """MEBBIS'ten çekilen başvuru ana bilgileri."""
    __tablename__ = "basvuru"

    id = db.Column(db.Integer, primary_key=True)
    basvuru_no = db.Column(db.String(50), unique=True, nullable=False)
    basvuru_tarihi = db.Column(db.String(20))
    basvuru_durumu = db.Column(db.String(50))

    # Kişisel Bilgiler
    tc_kimlik = db.Column(db.String(15))
    ad_soyad = db.Column(db.String(120))
    telefon = db.Column(db.String(30))
    eposta = db.Column(db.String(120))
    adres = db.Column(db.Text)

    # Başvuru Detayları
    basvuru_sekli = db.Column(db.String(100))
    basvuru_ulke = db.Column(db.String(100))
    meslek = db.Column(db.String(100))
    calistigi_kurum = db.Column(db.String(200))

    # Araştırma Bilgileri
    arastirma_adi = db.Column(db.Text)
    egitim_teknoloji = db.Column(db.String(50))
    arastirma_niteligi = db.Column(db.String(100))
    akademik_basari = db.Column(db.String(50))
    arastirma_konusu = db.Column(db.Text)
    anahtar_kelimeler = db.Column(db.Text)
    yazim_dili = db.Column(db.String(50))

    # Uygulama Bilgileri
    il_sayisi = db.Column(db.String(20))
    calisma_grubu = db.Column(db.Text)
    teskilat_turu = db.Column(db.String(100))
    meb_teskilati = db.Column(db.Text)
    okul_kurum_sayisi = db.Column(db.String(20))
    ozel_bilgiler = db.Column(db.Text)
    uygulama_suresi = db.Column(db.String(100))

    # Belge Linkleri (JSON string olarak saklanır)
    belge_arastirma_proje = db.Column(db.Text)
    belge_veri_toplama = db.Column(db.Text)
    belge_taahhutname = db.Column(db.Text)
    belge_etik_kurul = db.Column(db.Text)
    belge_gonullu_katilim = db.Column(db.Text)
    belge_veli_onam = db.Column(db.Text)
    belge_olcek_izni = db.Column(db.Text)
    belge_enstitu_karari = db.Column(db.Text)
    diger_ekler = db.Column(db.Text)

    # MEBBİS'ten çekilen değerlendirici bilgileri
    degerlendiriciler_mebbis = db.Column(db.Text)  # "Ad Soyad (Durum) | Ad Soyad (Durum)"

    # Değerlendirme durumu
    degerlendirme_durumu = db.Column(db.String(20), default="bekliyor")  # bekliyor, devam, tamamlandi
    yonetici_notu = db.Column(db.Text)
    koordinator_karari = db.Column(db.String(20)) # ONAY, RED
    koordinator_notu = db.Column(db.Text)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Yeni İş Akışı Alanları
    secilen_okul = db.Column(db.String(200))  # Koordinatör seçimi
    yonetici_notu = db.Column(db.Text)        # Yönetici red/onay notu

    # İlişkiler
    on_kontroller = db.relationship("OnKontrol", backref="basvuru", cascade="all, delete-orphan", lazy=True)
    kriterler = db.relationship("KriterDegerlendirme", backref="basvuru", cascade="all, delete-orphan", lazy=True)
    degerlendiriciler = db.relationship("BasvuruDegerlendirici", backref="basvuru", cascade="all, delete-orphan", lazy=True)

    def __repr__(self):
        return f"<Basvuru {self.basvuru_no}>"


# 12 ön kontrol maddesi sabitleri
ON_KONTROL_MADDELERI = [
    {"sira": 1, "ad": "Araştırma Başvuru Bilgileri/Tez Önerisi"},
    {"sira": 2, "ad": "Eğitim Öğretim İlişkisi"},
    {"sira": 3, "ad": "Taahhütname"},
    {"sira": 4, "ad": "Enstitü YK Kararı"},
    {"sira": 5, "ad": "Etik Kurul Onay Belgesi"},
    {"sira": 6, "ad": "Veri Toplama Araçları"},
    {"sira": 7, "ad": "Veri Toplama Aracı Kullanım İzni"},
    {"sira": 8, "ad": "Ayrıntılı Bilgilendirme ve Gönüllü Onam Formu"},
    {"sira": 9, "ad": "Veli Onam Formu"},
    {"sira": 10, "ad": "Tercüme"},
    {"sira": 11, "ad": "Evren Örneklem Uygunluğu"},
    {"sira": 12, "ad": "Araştırma Süresi"},
]


class OnKontrol(db.Model):
    """12 ön kontrol maddesi değerlendirmesi."""
    __tablename__ = "on_kontrol"

    id = db.Column(db.Integer, primary_key=True)
    basvuru_id = db.Column(db.Integer, db.ForeignKey("basvuru.id"), nullable=False)
    sira = db.Column(db.Integer, nullable=False)   # 1-12
    madde_adi = db.Column(db.String(200))
    durum = db.Column(db.String(10))                # VAR, YOK, N/A
    aciklama = db.Column(db.Text)

    __table_args__ = (db.UniqueConstraint("basvuru_id", "sira", name="uq_on_kontrol"),)


# 30 kriter sabitleri
KRITERLER = [
    {
        "no": 1,
        "metin": "Araştırma ve veri toplama araçlarının (anket, görüşme-gözlem formları) içeriği Türkiye Cumhuriyeti Anayasası, taraf olunan uluslararası anlaşmalar ve sözleşmeler başta olmak üzere, 6698 sayılı Kişisel Verilerin Korunması Kanunu ile yürürlükte olan tüm yasal düzenlemeler ve Türk millî eğitiminin genel ve özel amaçlarına uygun olacak şekilde hazırlanmıştır."
    },
    {"no": 2, "metin": "Araştırmacının kişisel bilgileri (adres, telefon, e-posta) belirtilmiştir."},
    {"no": 3, "metin": "Araştırmacının başvuru bilgileri (başvurunun yapıldığı ülke, başvuru şekli, başvuran ünvanı, meslek, çalıştığı kurum, bağlı olduğu kurum) belirtilmiştir."},
    {
        "no": 4,
        "metin": "Başvuru şekli kamu kurum/kuruluşu ya da sivil toplum kuruluşu temsilcileri ise kurum/kuruluşları veya sivil toplum kuruluşları adı, sorumlu kişinin ünvanı belirtilmiş ve «İlgili Araştırmayı Yürüteceğine Dair İmzalı İzin Belgesi» yüklenmiştir. Başvuru şekli millî eğitim müdürlüklerine bağlı birim temsilcileri ise «Araştırma Yürütülen Birimdeki En Üst Makamdan Alınan Olur» belgesi sisteme yüklenmiştir."
    },
    {"no": 5, "metin": "Araştırmacı öğrenci ise «Tez Önerisi» ve tez önerisinin onaylandığına dair «Enstitü Yönetim Kurulu Kararı/Resmî Yazı/Belge» yüklenmiştir."},
    {"no": 6, "metin": "Araştırmacı öğrenci değil ise Araştırma/Proje Bilgileri adlı belge yüklenmiştir. Araştırma/Proje Bilgileri adlı belgede olması gereken içerikler yer almıştır."},
    {"no": 7, "metin": "«Millî Eğitim Bakanlığı Araştırma Uygulama İzni Başvuru Taahhütnamesi» imzalı hâli yüklenmiştir."},
    {"no": 8, "metin": "«Yetkili Etik Kuruldan Alınan Onay Belgesi» yüklenmiştir."},
    {
        "no": 9,
        "metin": "Alan yazında daha önce kullanılmış veri toplama aracı tercih ediliyorsa «Veri Toplama Aracı Kullanım İzni» yüklenmiştir. Aracın kullanımına ilişkin izin gerekli değil ise araştırmacı açıklama yapmış, aracın geliştiricisine ve kaynağına yer vermiştir."
    },
    {"no": 10, "metin": "Araştırma uygulama izni başvurularında yabancı dilde hazırlanan belgeler için sisteme belgelerin asılları, Türkçe tercümeleri, Tercüme Doğruluk Beyanı yüklenmiştir."},
    {
        "no": 11,
        "metin": "«Ayrıntılı Bilgilendirme ve Gönüllü Katılım Formu» yüklenmiştir. Örneklemdeki/çalışma grubundaki kişilerin reşit olmamaları durumunda «Veli Onam Formu» yüklenmiştir. Araştırmada ses veya görüntü kaydı alınacaksa ses veya görüntü kaydına dair bilgilere öneride ya da araştırma/proje bilgileri adlı belgede yer verilmiştir."
    },
    {"no": 12, "metin": "Araştırmanın içeriği (başlığı) eğitim ve öğretim ile ilişkilidir. Başvuru «Araştırma Uygulama İzinleri Yönergesi» kapsamındadır."},
    {"no": 13, "metin": "Araştırmanın amacı eğitim ve öğretim ile ilişkilidir."},
    {"no": 14, "metin": "Araştırmanın problem durumu eğitim ve öğretim ile ilişkilidir."},
    {"no": 15, "metin": "Araştırmanın önemi eğitim ve öğretim ile ilişkilidir."},
    {"no": 16, "metin": "Araştırmanın modeli/deseni belirtilmiştir."},
    {
        "no": 17,
        "metin": "Araştırmanın örneklem/çalışma grubu belirtilmiştir. Sistemde yapılan seçimler ile Tez önerisi ya da Araştırma/Proje Bilgileri adlı belgede belirtilen örneklem/çalışma grubuna ilişkin bilgiler uyuşmaktadır. Araştırma kapsamında yer alan illerin hangi kriterlere göre seçildiğine ve örneklem büyüklüğüne ilişkin bilimsel bir açıklamaya yer verilmiştir."
    },
    {"no": 18, "metin": "Araştırmanın örneklemi/çalışma grubu ekonomik, ulaşılabilir ve uygulanabilir şekilde belirlenmiştir."},
    {"no": 19, "metin": "Veri toplama sürecine ilişkin bilgi verilmiştir."},
    {"no": 20, "metin": "Veri toplama aracı/araçlarının başlıkları ile sisteme yüklenen araç/araçlar aynıdır. Veri toplama araçlarının tamamı (anket, görüşme formu vb.) yüklenmiştir."},
    {"no": 21, "metin": "Veri toplama aracı/araçları araştırmanın amacına ve konusuna uygun şekilde belirlenmiştir."},
    {"no": 22, "metin": "Veri toplama aracı/araçlarındaki maddeler açık ve anlaşılır şekilde oluşturulmuştur."},
    {"no": 23, "metin": "Veri toplama aracı/araçlarındaki maddeler uygulama yapacağı grubun seviyesine uygun olarak hazırlanmıştır."},
    {"no": 24, "metin": "Veri analizine ilişkin bilgiye yer verilmiştir."},
    {"no": 25, "metin": "Kaynakça yer almaktadır."},
    {"no": 26, "metin": "Uygulama süresine ilişkin bilgiye yer verilmiştir."},
    {"no": 27, "metin": "Araştırmada katılımcıların kişilik haklarını, kurum ve kuruluşlarının haklarını ihlal eder nitelikte unsur(lar)a yer verilmemiştir."},
    {"no": 28, "metin": "İçerikteki unsurlarda millî ve manevi değerler, toplumsal hassasiyetler göz önünde bulundurulmuştur."},
    {
        "no": 29,
        "metin": "Araştırma kapsamında uygulama yapılacak örneklem/çalışma grubunun bizzat göreceği belgelerde (formlar, veri toplama araçları) veya araştırmanın başlığında herhangi bir kişi, kurum, ürün, organizasyon lehine veya aleyhine reklam unsuru yer almamaktadır."
    },
    {"no": 30, "metin": "Aynı araştırma ile ilgili mükerrer (tekrar eden) başvuru yapılmamıştır. Aynı araştırma kapsamında uygulama açısından bir farklılık gerekmedikçe yeni bir başvuru izninde bulunulmamıştır."},
]


class KriterDegerlendirme(db.Model):
    """30 kriter değerlendirmesi."""
    __tablename__ = "kriter_degerlendirme"

    id = db.Column(db.Integer, primary_key=True)
    basvuru_id = db.Column(db.Integer, db.ForeignKey("basvuru.id"), nullable=False)
    kriter_no = db.Column(db.Integer, nullable=False)  # 1-30
    sonuc = db.Column(db.String(15))                    # UYGUN, UYGUN_DEGIL, bos
    aciklama = db.Column(db.Text)

    __table_args__ = (db.UniqueConstraint("basvuru_id", "kriter_no", name="uq_kriter"),)


class BasvuruDegerlendirici(db.Model):
    """Her başvuruya atanan değerlendiriciler (en fazla 2)."""
    __tablename__ = "basvuru_degerlendirici"

    id = db.Column(db.Integer, primary_key=True)
    basvuru_id = db.Column(db.Integer, db.ForeignKey("basvuru.id"), nullable=False)
    degerlendirici_adi = db.Column(db.String(200), nullable=False)
    karar = db.Column(db.String(20))  # ONAY, RED, DUZELTME
    aciklama = db.Column(db.Text)     # Değerlendirici notu

    __table_args__ = (db.UniqueConstraint("basvuru_id", "degerlendirici_adi", name="uq_basvuru_deg"),)

class Degerlendirici(db.Model):
    """Sistemdeki kayıtlı değerlendiriciler."""
    __tablename__ = "degerlendirici"

    id = db.Column(db.Integer, primary_key=True)
    ad_soyad = db.Column(db.String(200), unique=True, nullable=False)
    aktif = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Degerlendirici {self.ad_soyad}>"
