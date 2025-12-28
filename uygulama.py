from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
import random
import json
from collections import Counter

app = Flask(__name__)
app.secret_key = 'cok_gizli_anahtar_proje_icin'

# --- SABİT LİSTELER ---
TETIK_BESLENME = [
    "Öğün Atlama", "Kafein Fazlalığı", "Çikolata", "Peynir", 
    "Alkol", "Susuzluk", "İşlenmiş Et", "Turşu/Fermante Gıda"
]

MIGREN_BILGILERI = [
    "Dünya Sağlık Örgütü'ne göre migren, dünyadaki en yaygın 3. hastalıktır.",
    "Kadınların migren geçirme olasılığı erkeklere göre 3 kat daha fazladır.",
    "Migren ataklarının %75'inden fazlası stres kaynaklı tetiklenir.",
    "Kafein, bazı kişilerde migreni tetiklerken bazılarında ağrıyı hafifletebilir.",
    "Düzenli uyku (günde 7-8 saat), migren ataklarını %40 oranında azaltabilir.",
    "Migren sadece bir baş ağrısı değildir; nörolojik bir hastalıktır."
]

# --- VERİTABANI BAĞLANTISI ---
def baglanti_kur():
    conn = sqlite3.connect('migren_projesi.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- YARDIMCI FONKSİYON: Tarih Temizleyici ---
def tarih_formatla(tarih_str):
    if not tarih_str: return ""
    try:
        temiz_tarih = tarih_str.split('.')[0] 
        obj = datetime.strptime(temiz_tarih, '%Y-%m-%d %H:%M:%S')
        return obj.strftime('%Y-%m-%d %H:%M')
    except:
        return tarih_str[:16]

# ================= ROTALAR =================

@app.route('/')
def index():
    if 'kullanici_id' in session:
        return redirect(url_for('panel'))
    return redirect(url_for('giris_yap'))

# --- GİRİŞ VE KAYIT ---
@app.route('/giris', methods=['GET', 'POST'])
def giris_yap():
    if request.method == 'POST':
        islem_tipi = request.form.get('islem_tipi') 
        conn = baglanti_kur()
        cursor = conn.cursor()

        if islem_tipi == 'giris':
            kadi = request.form['kullanici_adi']
            sifre = request.form['sifre']
            cursor.execute("SELECT * FROM kullanicilar WHERE kullanici_adi = ? AND sifre = ?", (kadi, sifre))
            kullanici = cursor.fetchone()
            
            if kullanici:
                session['kullanici_id'] = kullanici['id']
                session['ad'] = kullanici['ad_soyad'] if kullanici['ad_soyad'] else kullanici['kullanici_adi']
                return redirect(url_for('panel'))
            else:
                flash("Hatalı kullanıcı adı veya şifre!", "hata")

        elif islem_tipi == 'kayit':
            try:
                cursor.execute("INSERT INTO kullanicilar (ad_soyad, kullanici_adi, sifre, yas, cinsiyet) VALUES (?, ?, ?, ?, ?)",
                               (request.form['ad_soyad'], request.form['kullanici_adi'], request.form['sifre'], request.form['yas'], request.form['cinsiyet']))
                conn.commit()
                flash("Kayıt başarılı! Şimdi giriş yapabilirsiniz.", "basari")
            except sqlite3.IntegrityError:
                flash("Bu kullanıcı adı zaten alınmış.", "hata")
        
        conn.close()
    return render_template('giris.html')

# --- PANEL (ANA SAYFA) ---
@app.route('/panel')
def panel():
    if 'kullanici_id' not in session: return redirect(url_for('giris_yap'))
    
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    # Tablo için son 5 atak
    cursor.execute("SELECT * FROM ataklar WHERE kullanici_id = ? ORDER BY baslangic_zamani DESC LIMIT 5", (session['kullanici_id'],))
    ham_ataklar = cursor.fetchall()
    
    son_ataklar = []
    for atak in ham_ataklar:
        a_dict = dict(atak)
        a_dict['temiz_tarih'] = tarih_formatla(a_dict['baslangic_zamani'])
        son_ataklar.append(a_dict)

    # Grafik için tüm ataklar
    cursor.execute("SELECT baslangic_zamani, siddet FROM ataklar WHERE kullanici_id = ? ORDER BY baslangic_zamani ASC", (session['kullanici_id'],))
    tum_ataklar = cursor.fetchall()
    conn.close()

    grafik_tarihleri = [tarih_formatla(x['baslangic_zamani']) for x in tum_ataklar]
    grafik_siddetleri = [x['siddet'] for x in tum_ataklar]
    
    # GÜNCELLENDİ: Tek bilgi yerine tüm listeyi gönderiyoruz (Carousel için)
    return render_template('panel.html', 
                           isim=session['ad'], 
                           ataklar=son_ataklar, 
                           bilgi_listesi=MIGREN_BILGILERI, 
                           grafik_tarihleri=json.dumps(grafik_tarihleri),
                           grafik_siddetleri=json.dumps(grafik_siddetleri),
                           yemek_listesi=TETIK_BESLENME)

# --- TÜM ATAKLAR ---
@app.route('/tum-ataklar')
def tum_ataklar():
    if 'kullanici_id' not in session: return redirect(url_for('giris_yap'))
    
    conn = baglanti_kur()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ataklar WHERE kullanici_id = ? ORDER BY baslangic_zamani DESC", (session['kullanici_id'],))
    veriler = cursor.fetchall()
    conn.close()
    
    temiz_veriler = []
    for v in veriler:
        x = dict(v)
        x['temiz_tarih'] = tarih_formatla(x['baslangic_zamani'])
        temiz_veriler.append(x)
        
    return render_template('tum_ataklar.html', ataklar=temiz_veriler)

# --- ATAK EKLE (DÜZELTİLDİ: AĞRI TİPİ EKLENDİ) ---
@app.route('/atak-ekle', methods=['GET', 'POST'])
def atak_ekle():
    if 'kullanici_id' not in session: return redirect(url_for('giris_yap'))
    
    if request.method == 'POST':
        try:
            # 1. Aşama
            baslangic = request.form['baslangic']
            bitis = request.form.get('bitis')
            if not bitis: bitis = baslangic 

            t1 = datetime.strptime(baslangic, '%Y-%m-%dT%H:%M')
            t2 = datetime.strptime(bitis, '%Y-%m-%dT%H:%M')
            sure_dk = int((t2 - t1).total_seconds() / 60)
            if sure_dk < 0: sure_dk = 0

            # 2. Aşama (Şiddet ve Konum)
            siddet = request.form.get('siddet')
            konumlar = request.form.get('konumlar') # "agri_konumu" yerine "konumlar" kullanıyoruz genel olarak
            
            # 3. Aşama (Semptomlar ve YENİ: AĞRI TİPİ)
            semptomlar = request.form.get('semptomlar')
            agri_tipleri = request.form.get('agri_tipleri') # <-- YENİ EKLENDİ

            # 4. Aşama
            tetikleyiciler = request.form.get('tetikleyiciler')

            # 5. Aşama
            ilaclar = request.form.get('ilaclar')
            rahatlama = request.form.get('rahatlama')
            notlar = request.form.get('notlar')

            # Veritabanına Kayıt
            conn = baglanti_kur()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ataklar (
                    kullanici_id, baslangic_zamani, bitis_zamani, sure_dk, siddet, 
                    agri_konumu, agri_tipleri, semptomlar, tetikleyiciler, ilaclar, rahatlama_yontemleri, notlar
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (session['kullanici_id'], baslangic, bitis, sure_dk, siddet, 
                  konumlar, agri_tipleri, semptomlar, tetikleyiciler, ilaclar, rahatlama, notlar))
            
            conn.commit()
            conn.close()
            
            flash("Atak kaydı başarıyla tamamlandı! Geçmiş olsun.", "basari")
            return redirect(url_for('panel'))
            
        except Exception as e:
            flash(f"Hata oluştu: {e}", "hata")
            
    return render_template('atak_ekle.html')

# --- ANALİZ (GÜNCELLENDİ: AĞRI TİPİ GRAFİĞİ EKLENDİ) ---
@app.route('/analiz')
def analiz():
    if 'kullanici_id' not in session: return redirect(url_for('giris_yap'))
    
    conn = baglanti_kur()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ataklar WHERE kullanici_id = ? ORDER BY baslangic_zamani ASC", (session['kullanici_id'],))
    veriler = cursor.fetchall()
    conn.close()
    
    toplam_atak = len(veriler)
    if toplam_atak == 0:
        return render_template('analiz.html', veri_yok=True, isim=session['ad'])

    toplam_siddet = sum([v['siddet'] for v in veriler])
    ortalama_siddet = round(toplam_siddet / toplam_atak, 1)
    
    toplam_sure = sum([v['sure_dk'] for v in veriler])
    ortalama_sure = int(toplam_sure / toplam_atak)

    # Listeler
    list_tetik = []
    list_konum = []
    list_ilac = []
    list_rahatlama = []
    list_besin = []
    list_agri_tipi = [] # <-- YENİ

    BESINLER = ["Ogun_Atlama", "Kafein_Fazlaligi", "Cikolata", "Peynir", "Alkol", "Susuzluk", "Islenmis_Et", "Tursu_Fermante"]
    saat_dagilimi = {"06-12 (Sabah)": 0, "12-18 (Öğle)": 0, "18-24 (Akşam)": 0, "00-06 (Gece)": 0}

    for v in veriler:
        # Tetikleyiciler
        if v['tetikleyiciler']: 
            items = [x.strip() for x in v['tetikleyiciler'].split(',') if x.strip()]
            list_tetik.extend(items)
            for i in items:
                if i in BESINLER: list_besin.append(i)

        # Ağrı Tipi (YENİ)
        if v['agri_tipleri']:
            items = [x.strip() for x in v['agri_tipleri'].split(',') if x.strip()]
            list_agri_tipi.extend(items)

        # Diğerleri
        if v['agri_konumu']: list_konum.extend([x.strip() for x in v['agri_konumu'].split(',') if x.strip()])
        if v['ilaclar']: list_ilac.extend([x.strip() for x in v['ilaclar'].split(',') if x.strip()])
        if v['rahatlama_yontemleri']: list_rahatlama.extend([x.strip() for x in v['rahatlama_yontemleri'].split(',') if x.strip()])
        
        # Saat Analizi
        try:
            tarih_str = v['baslangic_zamani']
            if 'T' in tarih_str: saat = int(tarih_str.split('T')[1].split(':')[0])
            elif ' ' in tarih_str: saat = int(tarih_str.split(' ')[1].split(':')[0])
            else: saat = 0 
            
            if 6 <= saat < 12: saat_dagilimi["06-12 (Sabah)"] += 1
            elif 12 <= saat < 18: saat_dagilimi["12-18 (Öğle)"] += 1
            elif 18 <= saat <= 23: saat_dagilimi["18-24 (Akşam)"] += 1
            else: saat_dagilimi["00-06 (Gece)"] += 1
        except: pass

    # Counter İşlemleri
    c_tetik = Counter(list_tetik).most_common(5)
    c_konum = Counter(list_konum).most_common(5)
    c_ilac = Counter(list_ilac).most_common(5)
    c_rahat = Counter(list_rahatlama).most_common(5)
    c_besin = Counter(list_besin).most_common(5)
    c_agri_tipi = Counter(list_agri_tipi).most_common(5) # <-- YENİ
    
    bas_dusman = c_tetik[0][0] if c_tetik else "Tespit Edilemedi"
    favori_rahatlama = c_rahat[0][0] if c_rahat else "Dinlenme"
    oneri = f"Verilerine göre '{favori_rahatlama}' sana en iyi gelen yöntem." if c_rahat else "Henüz yeterli veri yok."

    guven_orani = int((toplam_atak / 20) * 100)
    if guven_orani > 100: guven_orani = 100

    return render_template('analiz.html', 
                           veri_yok=False, isim=session['ad'],
                           toplam_atak=toplam_atak, ortalama_siddet=ortalama_siddet, ortalama_sure=ortalama_sure,
                           bas_dusman=bas_dusman, guven_orani=guven_orani, oneri=oneri,
                           # Grafikler
                           lbl_tetik=json.dumps([x[0] for x in c_tetik]), val_tetik=json.dumps([x[1] for x in c_tetik]),
                           lbl_konum=json.dumps([x[0] for x in c_konum]), val_konum=json.dumps([x[1] for x in c_konum]),
                           lbl_ilac=json.dumps([x[0] for x in c_ilac]), val_ilac=json.dumps([x[1] for x in c_ilac]),
                           lbl_rahat=json.dumps([x[0] for x in c_rahat]), val_rahat=json.dumps([x[1] for x in c_rahat]),
                           lbl_besin=json.dumps([x[0] for x in c_besin]), val_besin=json.dumps([x[1] for x in c_besin]),
                           lbl_agri_tipi=json.dumps([x[0] for x in c_agri_tipi]), val_agri_tipi=json.dumps([x[1] for x in c_agri_tipi]), # <-- YENİ
                           lbl_saat=json.dumps(list(saat_dagilimi.keys())), val_saat=json.dumps(list(saat_dagilimi.values()))
                           )

# --- TAHMİN YAP ---
@app.route('/tahmin-yap', methods=['POST'])
def tahmin_yap():
    if 'kullanici_id' not in session: return redirect(url_for('giris_yap'))

    conn = baglanti_kur()
    cursor = conn.cursor()
    cursor.execute("SELECT tetikleyiciler FROM ataklar WHERE kullanici_id = ?", (session['kullanici_id'],))
    gecmis_ataklar = cursor.fetchall()
    conn.close()

    if len(gecmis_ataklar) < 1:
        session['tahmin_sonucu'] = {'puan': 0, 'durum': "Veri Yetersiz", 'nedenler': ["Analiz için en az 1 atak girmelisin."]}
        return redirect(url_for('panel'))

    list_tetik = []
    for atak in gecmis_ataklar:
        if atak['tetikleyiciler']:
            list_tetik.extend([x.strip() for x in atak['tetikleyiciler'].split(',') if x.strip()])
    istatistik = Counter(list_tetik)

    try:
        raw_su = request.form.get('su_miktari', '0')
        su_icilen = float(raw_su) if raw_su else 0.0

        raw_uyku = request.form.get('uyku_suresi', '420')
        uyku_suresi = int(raw_uyku) if raw_uyku else 420

        raw_stres = request.form.get('stres_seviyesi', '0')
        stres_seviyesi = int(raw_stres) if raw_stres else 0
    except ValueError:
        su_icilen = 0.0; uyku_suresi = 420; stres_seviyesi = 0

    yenilenler = request.form.getlist('yenilenler[]')

    puan = 0
    nedenler = []

    if uyku_suresi < 360:
        puan += 30 if istatistik['Uykusuzluk'] > 0 else 10
        nedenler.append("Yetersiz uyku riski artırıyor.")

    if stres_seviyesi >= 7:
        puan += 40 if istatistik['Yogun_Stres'] > 0 else 20
        nedenler.append("Yüksek stres seviyesi.")

    if su_icilen < 2.0:
        puan += 15
        nedenler.append("Az su tüketimi.")

    for y in yenilenler:
        if istatistik[y] > 0:
            puan += 25
            nedenler.append(f"{y} geçmişte tetikleyici olmuş.")

    if puan > 100: puan = 100
    durum = "Düşük Risk 🟢"
    if puan > 35: durum = "Orta Risk 🟡"
    if puan > 70: durum = "YÜKSEK RİSK 🔴"

    session['tahmin_sonucu'] = {'puan': puan, 'durum': durum, 'nedenler': nedenler}
    return redirect(url_for('panel'))

@app.route('/cikis')
def cikis():
    session.clear()
    return redirect(url_for('giris_yap'))

if __name__ == '__main__':
    app.run(debug=True)