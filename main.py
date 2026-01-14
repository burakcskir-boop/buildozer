from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
import sqlite3
from datetime import date, timedelta

Window.size = (360, 640)
Window.softinput_mode = "below_target"

# ================= DATABASE =================
class Database:
    DB = "paketleme.db"

    @staticmethod
    def connect():
        return sqlite3.connect(Database.DB)

    @staticmethod
    def column_exists(c, table, column):
        c.execute(f"PRAGMA table_info({table})")
        return column in [i[1] for i in c.fetchall()]

    @staticmethod
    def init():
        conn = Database.connect()
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS calisanlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isim TEXT UNIQUE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS isler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isim TEXT UNIQUE
        )
        """)
        if not Database.column_exists(c, "isler", "fiyat"):
            c.execute("ALTER TABLE isler ADD COLUMN fiyat REAL DEFAULT 0")

        c.execute("""
        CREATE TABLE IF NOT EXISTS kayitlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calisan_id INTEGER,
            is_adi TEXT,
            adet INTEGER,
            fiyat REAL,
            tarih TEXT
        )
        """)
        if not Database.column_exists(c, "kayitlar", "odendi"):
            c.execute("ALTER TABLE kayitlar ADD COLUMN odendi INTEGER DEFAULT 0")

        conn.commit()
        conn.close()

# ================= SERVICE =================
class Service:

    @staticmethod
    def calisanlar():
        conn = Database.connect()
        c = conn.cursor()
        c.execute("SELECT id, isim FROM calisanlar ORDER BY isim")
        d = c.fetchall()
        conn.close()
        return d

    @staticmethod
    def calisan_ekle(isim):
        conn = Database.connect()
        c = conn.cursor()
        c.execute("INSERT INTO calisanlar VALUES (NULL,?)", (isim,))
        conn.commit()
        conn.close()

    @staticmethod
    def isler():
        conn = Database.connect()
        c = conn.cursor()
        c.execute("SELECT isim, fiyat FROM isler ORDER BY isim")
        d = c.fetchall()
        conn.close()
        return d

    @staticmethod
    def is_ekle(isim, fiyat):
        conn = Database.connect()
        c = conn.cursor()
        c.execute("""
        INSERT INTO isler (isim, fiyat)
        VALUES (?,?)
        ON CONFLICT(isim) DO UPDATE SET fiyat=excluded.fiyat
        """, (isim, fiyat))
        conn.commit()
        conn.close()

    @staticmethod
    def kayit_ekle(cid, is_adi, adet, fiyat):
        conn = Database.connect()
        c = conn.cursor()
        c.execute("""
        INSERT INTO kayitlar VALUES (NULL,?,?,?,?,?,0)
        """, (cid, is_adi, adet, fiyat, date.today().isoformat()))
        conn.commit()
        conn.close()

    @staticmethod
    def rapor(cid, gun):
        conn = Database.connect()
        c = conn.cursor()
        if gun == 0:
            c.execute("""
            SELECT is_adi, SUM(adet), fiyat
            FROM kayitlar
            WHERE calisan_id=? AND tarih=? AND odendi=0
            GROUP BY is_adi
            """, (cid, date.today().isoformat()))
        else:
            bas = (date.today() - timedelta(days=gun)).isoformat()
            c.execute("""
            SELECT is_adi, SUM(adet), fiyat
            FROM kayitlar
            WHERE calisan_id=? AND tarih>=? AND odendi=0
            GROUP BY is_adi
            """, (cid, bas))
        d = c.fetchall()
        conn.close()
        return d

    @staticmethod
    def odeme_yap(cid):
        conn = Database.connect()
        c = conn.cursor()
        c.execute("UPDATE kayitlar SET odendi=1 WHERE calisan_id=? AND odendi=0", (cid,))
        conn.commit()
        conn.close()

# ================= RAPOR =================
class RaporPopup(Popup):
    def __init__(self, cid, isim, data):
        super().__init__(title="RAPOR", size_hint=(0.9,0.85))
        self.cid = cid

        box = BoxLayout(orientation="vertical", padding=10, spacing=5)
        box.add_widget(Label(text=isim, size_hint_y=None, height=30))

        grid = GridLayout(cols=1, size_hint_y=None, spacing=5)
        grid.bind(minimum_height=grid.setter("height"))

        toplam = 0
        for is_adi, adet, fiyat in data:
            tutar = adet * fiyat
            toplam += tutar
            grid.add_widget(Label(
                text=f"{is_adi} | {adet} adet | {tutar:.2f} TL",
                size_hint_y=None, height=30
            ))

        scroll = ScrollView()
        scroll.add_widget(grid)
        box.add_widget(scroll)

        box.add_widget(Label(text=f"TOPLAM: {toplam:.2f} TL",
                             size_hint_y=None, height=40))

        btn = Button(text="ÖDEME YAPILDI", size_hint_y=None, height=45)
        btn.bind(on_press=self.odeme)
        box.add_widget(btn)

        self.content = box

    def odeme(self, _):
        Service.odeme_yap(self.cid)
        self.dismiss()
        Popup(title="OK",
              content=Label(text="Ödeme yapıldı, bakiye sıfırlandı"),
              size_hint=(0.8,0.4)).open()

# ================= ANA EKRAN =================
class AnaEkran(BoxLayout):
    def __init__(self):
        super().__init__(orientation="vertical", padding=10, spacing=8)
        self.cid = None
        self.cadi = None
        self.is_fiyat = {}

        self.add_widget(Label(text="PAKETLEME TAKİP", font_size=18,
                              size_hint_y=None, height=40))

        self.yeni = TextInput(hint_text="Yeni Çalışan", multiline=False)
        b = Button(text="Ekle")
        b.bind(on_press=self.calisan_ekle)
        ust = BoxLayout(size_hint_y=None, height=40)
        ust.add_widget(self.yeni)
        ust.add_widget(b)
        self.add_widget(ust)

        self.liste = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.liste.bind(minimum_height=self.liste.setter("height"))
        sc = ScrollView(size_hint=(1,0.3))
        sc.add_widget(self.liste)
        self.add_widget(sc)

        self.spinner = Spinner(text="İş Türü Seç", size_hint_y=None, height=40)
        self.spinner.bind(text=self.is_secildi)

        self.is_input = TextInput(hint_text="Yeni iş türü (opsiyonel)", multiline=False)
        self.fiyat_input = TextInput(hint_text="Birim Fiyat", input_filter="float", multiline=False)
        self.adet_input = TextInput(hint_text="Adet", input_filter="int", multiline=False)

        for w in [self.spinner, self.is_input, self.fiyat_input, self.adet_input]:
            self.add_widget(w)

        btn = Button(text="Kayıt Ekle", size_hint_y=None, height=40)
        btn.bind(on_press=self.kaydet)
        self.add_widget(btn)

        alt = BoxLayout(size_hint_y=None, height=40)
        for t,g in [("Bugün",0),("Hafta",7),("Ay",30)]:
            bb = Button(text=t)
            bb.bind(on_press=lambda x, gg=g: self.rapor(gg))
            alt.add_widget(bb)
        self.add_widget(alt)

        self.yukle()

    def popup(self, t, m):
        Popup(title=t, content=Label(text=m),
              size_hint=(0.8,0.4)).open()

    def yukle(self):
        self.liste.clear_widgets()
        for cid, isim in Service.calisanlar():
            b = Button(text=isim, size_hint_y=None, height=35)
            b.bind(on_press=lambda x, i=cid, a=isim: self.sec(i,a))
            self.liste.add_widget(b)

        self.is_fiyat = {i:f for i,f in Service.isler()}
        self.spinner.values = list(self.is_fiyat.keys())

    def is_secildi(self, _, text):
        if text in self.is_fiyat:
            self.fiyat_input.text = str(self.is_fiyat[text])

    def sec(self, cid, adi):
        self.cid = cid
        self.cadi = adi
        self.popup("Seçildi", adi)

    def calisan_ekle(self, _):
        try:
            Service.calisan_ekle(self.yeni.text.strip())
            self.yeni.text=""
            self.yukle()
        except:
            self.popup("Hata","İsim mevcut veya hatalı")

    def kaydet(self, _):
        if not self.cid:
            self.popup("Hata","Çalışan seç")
            return

        is_adi = self.is_input.text.strip() or self.spinner.text
        fiyat = float(self.fiyat_input.text)
        adet = int(self.adet_input.text)

        Service.is_ekle(is_adi, fiyat)
        Service.kayit_ekle(self.cid, is_adi, adet, fiyat)

        self.is_input.text=""
        self.adet_input.text=""
        self.popup("OK","Kayıt eklendi")
        self.yukle()

    def rapor(self, gun):
        RaporPopup(self.cid, self.cadi, Service.rapor(self.cid, gun)).open()

# ================= APP =================
class PaketlemeApp(App):
    def build(self):
        Database.init()
        return AnaEkran()

if __name__ == "__main__":
    PaketlemeApp().run()
