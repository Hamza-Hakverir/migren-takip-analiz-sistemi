import sqlite3
import random
from datetime import datetime, timedelta

# --- AYARLAR ---
DB_NAME = "migren_projesi.db"
GUN_SAYISI = 60 

# --- SABİT VERİ LİSTELERİ ---
AGRI_TIPLERI = ["Zonklayici", "Cekicle_Vurulur_Gibi", "Sikistirici", "Yururken_Artan", "Saplanan", "Patlayici"]

SEMPTOM_DUYUSAL = ["Isik_Hassasiyeti", "Ses_Hassasiyeti", "Koku_Hassasiyeti"]
SEMPTOM_FIZIKSEL = ["Mide_Bulantisi", "Kusma", "Boyun_Agrisi", "Bas_Donmesi", "Terleme"]
SEMPTOM_PSIKOLOJIK = ["Kaygi_Anksiyete", "Depresif_Ruh_Hali", "Sinirlilik", "Odaklanma_Sorunu"]

TETIK_UYKU = ["Uykusuzluk", "Gec_Uyanma", "Bolunmus_Uyku", "Cok_Uyuma"]
TETIK_HAVA = ["Firtina_Lodos", "Yuksek_Nem", "Basinc_Degisimi", "Parlak_Gunes", "Aşırı_Sicak"]
TETIK_BESLENME = ["Ogun_Atlama", "Kafein_Fazlaligi", "Cikolata", "Peynir", "Alkol", "Susuzluk", "Islenmis_Et", "Tursu_Fermante"]
TETIK_DUYGU = ["Yogun_Stres", "Uzuntu", "Heyecan", "Panik"]

ILACLAR_HAFIF = ["Parol", "Vermidon", "Minoset"]
ILACLAR_ORTA = ["Majezik", "Arveles", "Dolorex", "Apranax", "Dexday"]
ILACLAR_MIGREN = ["Relpax", "Avmigran", "Zomig", "Cataflam", "Migrex"]

RAHATLAMA = ["Karanlik_Oda", "Uyku", "Soguk_Kompres", "Dus_Alma", "Masaj", "Kafein_Alimi", "Meditasyon", "Hareketsizlik"]

KONUMLAR = ["Sag_Sakak", "Sol_Sakak", "Ense", "Goz_Arkasi", "Alin", "Tepesi", "Butun_Bas"]

# --- VERİTABANI OLUŞTURMA ---
def veritabani_kur():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Temiz kurulum için önce eski tabloları kaldırıyoruz
    cursor.execute("DROP TABLE IF EXISTS ataklar")
    cursor.execute("DROP TABLE IF EXISTS kullanicilar")

    # 1. Kullanıcılar Tablosu
    cursor.execute('''
        CREATE TABLE kullanicilar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT,
            kullanici_adi TEXT UNIQUE,
            sifre TEXT,
            yas INTEGER,
            cinsiyet TEXT
        )
    ''')

    # 2. Ataklar Tablosu
    cursor.execute('''
        CREATE TABLE ataklar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kullanici_id INTEGER,
            baslangic_zamani DATETIME,
            bitis_zamani DATETIME,
            sure_dk INTEGER,
            siddet INTEGER, 
            agri_tipleri TEXT,       
            semptomlar TEXT,         
            tetikleyiciler TEXT,     
            ilaclar TEXT,
            rahatlama_yontemleri TEXT,
            agri_konumu TEXT,
            notlar TEXT,
            FOREIGN KEY(kullanici_id) REFERENCES kullanicilar(id)
        )
    ''')
    
    conn.commit()
    print("✅ Tablolar başarıyla oluşturuldu.")
    return conn

def coklu_secim(liste_havuzu, min_secim=0, max_secim=2):
    sayi = random.randint(min_secim, max_secim)
    if sayi == 0: return ""
    secilenler = random.sample(liste_havuzu, sayi)
    return ", ".join(secilenler)

def veri_uret(conn, ad_soyad, kullanici_adi, profil_tipi):
    cursor = conn.cursor()
    
    # Kullanıcı Ekleme
    try:
        cursor.execute("INSERT INTO kullanicilar (ad_soyad, kullanici_adi, sifre, yas, cinsiyet) VALUES (?, ?, ?, ?, ?)", 
                       (ad_soyad, kullanici_adi, "1234", 24, "K" if profil_tipi == "hassas" else "E"))
        kullanici_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        cursor.execute("SELECT id FROM kullanicilar WHERE kullanici_adi=?", (kullanici_adi,))
        kullanici_id = cursor.fetchone()[0]

    print(f"🔄 {kullanici_adi} ({ad_soyad}) için veriler üretiliyor...")

    baslangic = datetime.now() - timedelta(days=GUN_SAYISI)

    for i in range(GUN_SAYISI):
        gun = baslangic + timedelta(days=i)
        
        # Atak olma olasılığı
        if random.random() < 0.40: 
            if profil_tipi == "hassas": 
                tetik_liste = TETIK_HAVA + TETIK_DUYGU + ["Koku_Hassasiyeti"]
                siddet = random.randint(7, 10)
            else: 
                tetik_liste = TETIK_BESLENME + TETIK_UYKU
                siddet = random.randint(3, 8)

            # Veri Seçimleri
            secilen_agri_tipi = coklu_secim(AGRI_TIPLERI, 1, 2)
            
            s_duyusal = coklu_secim(SEMPTOM_DUYUSAL, 1, 2)
            s_fiziksel = coklu_secim(SEMPTOM_FIZIKSEL, 0, 2)
            s_psiko = coklu_secim(SEMPTOM_PSIKOLOJIK, 0, 1)
            full_semptomlar = ", ".join(filter(None, [s_duyusal, s_fiziksel, s_psiko]))

            t_ana = coklu_secim(tetik_liste, 1, 3) 
            t_yan = coklu_secim(TETIK_HAVA + TETIK_BESLENME, 0, 1) 
            full_tetikleyiciler = ", ".join(filter(None, [t_ana, t_yan]))

            if siddet >= 8: secilen_ilac = coklu_secim(ILACLAR_MIGREN, 1, 1)
            elif siddet >= 5: secilen_ilac = coklu_secim(ILACLAR_ORTA, 1, 1)
            else: secilen_ilac = coklu_secim(ILACLAR_HAFIF + ["Ilac_Alinmadi"], 1, 1)

            rahatlama = coklu_secim(RAHATLAMA, 1, 2)
            konum = coklu_secim(KONUMLAR, 1, 2)

            saat = random.randint(8, 22)
            atak_basi = gun.replace(hour=saat, minute=random.randint(0, 59))
            sure = random.randint(3, 18) 
            atak_sonu = atak_basi + timedelta(hours=sure)
            sure_dk = sure * 60

            # Atak Kaydetme
            cursor.execute('''
                INSERT INTO ataklar (
                    kullanici_id, baslangic_zamani, bitis_zamani, sure_dk, siddet, 
                    agri_tipleri, semptomlar, tetikleyiciler, ilaclar, rahatlama_yontemleri, agri_konumu
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (kullanici_id, atak_basi, atak_sonu, sure_dk, siddet, 
                  secilen_agri_tipi, full_semptomlar, full_tetikleyiciler, secilen_ilac, rahatlama, konum))

    conn.commit()
    print(f"✅ {kullanici_adi} tamamlandı.")

# --- ÇALIŞTIRMA ---
if __name__ == "__main__":
    baglanti = veritabani_kur()
    veri_uret(baglanti, "Fatma Yılmaz", "user_migren", "hassas")   
    veri_uret(baglanti, "Ahmet Demir", "user_gerilim", "normal")  
    baglanti.close()
    print("\n🎉 Veritabanı (migren_projesi.db) başarıyla yenilendi.")