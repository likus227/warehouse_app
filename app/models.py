from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum
import enum

db = SQLAlchemy()

# Enumeracje zgodne z diagramem
class RolaUzytkownika(enum.Enum):
    ADMINISTRATOR = "Administrator"
    SPRZEDAWCA = "Sprzedawca"
    MAGAZYNIER = "Magazynier"
    KIEROWNIK = "Kierownik"

class StatusZamowienia(enum.Enum):
    NOWE = "Nowe"
    W_REALIZACJI = "W realizacji"
    GOTOWE = "Gotowe"
    WYSLANE = "Wysłane"
    ANULOWANE = "Anulowane"

class StatusZamowieniaZakupu(enum.Enum):
    NOWE = "Nowe"
    WYSLANE = "Wysłane"
    DOSTARCZONE = "Dostarczone"
    ANULOWANE = "Anulowane"

class TypDokumentu(enum.Enum):
    PRZYJECIE = "PZ"
    WYDANIE = "WZ"

# Tabela pośrednia dla związku wiele-do-wielu
pozycje_zamowienia = db.Table('pozycje_zamowienia',
    db.Column('zamowienie_id', db.Integer, db.ForeignKey('zamowienie.id'), primary_key=True),
    db.Column('pozycja_id', db.Integer, db.ForeignKey('pozycja_zamowienia.id'), primary_key=True)
)

pozycje_zamowienia_zakupu = db.Table('pozycje_zamowienia_zakupu',
    db.Column('zamowienie_zakupu_id', db.Integer, db.ForeignKey('zamowienie_zakupu.id'), primary_key=True),
    db.Column('pozycja_id', db.Integer, db.ForeignKey('pozycja_zamowienia_zakupu.id'), primary_key=True)
)

# Klasa Uzytkownik
class Uzytkownik(db.Model):
    __tablename__ = 'uzytkownik'
    
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False)
    haslo_hash = db.Column(db.String(255), nullable=False)
    imie = db.Column(db.String(50), nullable=False)
    nazwisko = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    rola = db.Column(Enum(RolaUzytkownika), nullable=False)
    aktywny = db.Column(db.Boolean, default=True)
    data_utworzenia = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacje
    logi = db.relationship('Log', backref='uzytkownik', lazy=True)
    
    def ustaw_haslo(self, haslo):
        """Ustawia zahashowane hasło"""
        self.haslo_hash = generate_password_hash(haslo)
    
    def sprawdz_haslo(self, haslo):
        """Sprawdza poprawność hasła"""
        return check_password_hash(self.haslo_hash, haslo)
    
    def __repr__(self):
        return f'<Uzytkownik {self.login}>'

# Klasa Produkt
class Produkt(db.Model):
    __tablename__ = 'produkt'
    
    id = db.Column(db.Integer, primary_key=True)
    kod = db.Column(db.String(50), unique=True, nullable=False)
    nazwa = db.Column(db.String(200), nullable=False)
    kategoria = db.Column(db.String(100))
    jednostka = db.Column(db.String(20), default='szt')
    cena_jednostkowa = db.Column(db.Numeric(10, 2), nullable=False)
    stan_minimalny = db.Column(db.Integer, default=10)
    opis = db.Column(db.Text)
    aktywny = db.Column(db.Boolean, default=True)
    data_utworzenia = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacje
    stan_magazynowy = db.relationship('StanMagazynowy', backref='produkt', uselist=False)
    pozycje_dokumentow = db.relationship('PozycjaDokumentu', backref='produkt', lazy=True)
    
    def __repr__(self):
        return f'<Produkt {self.kod} - {self.nazwa}>'

# Klasa StanMagazynowy
class StanMagazynowy(db.Model):
    __tablename__ = 'stan_magazynowy'
    
    id = db.Column(db.Integer, primary_key=True)
    produkt_id = db.Column(db.Integer, db.ForeignKey('produkt.id'), nullable=False, unique=True)
    ilosc_dostepna = db.Column(db.Integer, default=0)
    ilosc_zarezerwowana = db.Column(db.Integer, default=0)
    lokalizacja = db.Column(db.String(50))
    ostatnia_aktualizacja = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def aktualizuj_stan(self, ilosc, operacja='dodaj'):
        """Aktualizuje stan magazynowy"""
        if operacja == 'dodaj':
            self.ilosc_dostepna += ilosc
        elif operacja == 'odejmij':
            self.ilosc_dostepna -= ilosc
        self.ostatnia_aktualizacja = datetime.utcnow()
    
    def rezerwuj(self, ilosc):
        """Rezerwuje ilość produktu"""
        if self.ilosc_dostepna >= ilosc:
            self.ilosc_dostepna -= ilosc
            self.ilosc_zarezerwowana += ilosc
            return True
        return False
    
    def czy_niski_stan(self):
        """Sprawdza czy stan jest niski"""
        return self.ilosc_dostepna <= self.produkt.stan_minimalny
    
    def __repr__(self):
        return f'<StanMagazynowy {self.produkt.kod}: {self.ilosc_dostepna}>'

# Klasa Klient
class Klient(db.Model):
    __tablename__ = 'klient'
    
    id = db.Column(db.Integer, primary_key=True)
    nazwa = db.Column(db.String(200), nullable=False)
    nip = db.Column(db.String(15), unique=True)
    adres = db.Column(db.String(200))
    kod_pocztowy = db.Column(db.String(10))
    miasto = db.Column(db.String(100))
    telefon = db.Column(db.String(20))
    email = db.Column(db.String(100))
    aktywny = db.Column(db.Boolean, default=True)
    data_utworzenia = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacje
    zamowienia = db.relationship('Zamowienie', backref='klient', lazy=True)
    faktury = db.relationship('Faktura', backref='klient', lazy=True)
    
    def __repr__(self):
        return f'<Klient {self.nazwa}>'

# Klasa Dostawca
class Dostawca(db.Model):
    __tablename__ = 'dostawca'
    
    id = db.Column(db.Integer, primary_key=True)
    nazwa = db.Column(db.String(200), nullable=False)
    nip = db.Column(db.String(15), unique=True)
    adres = db.Column(db.String(200))
    telefon = db.Column(db.String(20))
    email = db.Column(db.String(100))
    kontakt_osoba = db.Column(db.String(100))
    aktywny = db.Column(db.Boolean, default=True)
    
    # Relacje
    zamowienia_zakupu = db.relationship('ZamowienieZakupu', backref='dostawca', lazy=True)
    
    def __repr__(self):
        return f'<Dostawca {self.nazwa}>'

# Klasa Zamowienie
class Zamowienie(db.Model):
    __tablename__ = 'zamowienie'
    
    id = db.Column(db.Integer, primary_key=True)
    numer = db.Column(db.String(50), unique=True, nullable=False)
    klient_id = db.Column(db.Integer, db.ForeignKey('klient.id'), nullable=False)
    data_zamowienia = db.Column(db.DateTime, default=datetime.utcnow)
    data_realizacji = db.Column(db.DateTime)
    status = db.Column(Enum(StatusZamowienia), default=StatusZamowienia.NOWE)
    wartosc_netto = db.Column(db.Numeric(10, 2), default=0)
    wartosc_brutto = db.Column(db.Numeric(10, 2), default=0)
    uwagi = db.Column(db.Text)
    
    # Relacje
    pozycje = db.relationship('PozycjaZamowienia', secondary=pozycje_zamowienia, 
                             backref=db.backref('zamowienia', lazy=True))
    faktura = db.relationship('Faktura', backref='zamowienie', uselist=False)
    
    def oblicz_wartosc(self):
        """Oblicza wartość zamówienia na podstawie pozycji"""
        from decimal import Decimal
        netto = sum(p.wartosc_netto for p in self.pozycje)
        self.wartosc_netto = netto
        self.wartosc_brutto = netto * Decimal('1.23')
        
    def zmien_status(self, nowy_status):
        """Zmienia status zamówienia"""
        self.status = nowy_status
        if nowy_status == StatusZamowienia.GOTOWE:
            self.data_realizacji = datetime.utcnow()
    
    def __repr__(self):
        return f'<Zamowienie {self.numer}>'

# Klasa PozycjaZamowienia
class PozycjaZamowienia(db.Model):
    __tablename__ = 'pozycja_zamowienia'
    
    id = db.Column(db.Integer, primary_key=True)
    produkt_id = db.Column(db.Integer, db.ForeignKey('produkt.id'), nullable=False)
    ilosc = db.Column(db.Integer, nullable=False)
    cena_jednostkowa = db.Column(db.Numeric(10, 2), nullable=False)
    wartosc_netto = db.Column(db.Numeric(10, 2))
    skompletowane = db.Column(db.Boolean, default=False)
    
    # Relacja do produktu
    produkt_rel = db.relationship('Produkt', backref='pozycje_zamowien')
    
    def oblicz_wartosc(self):
        """Oblicza wartość pozycji"""
        self.wartosc_netto = self.ilosc * self.cena_jednostkowa
    
    def __repr__(self):
        return f'<PozycjaZamowienia {self.id}>'

# Klasa ZamowienieZakupu
class ZamowienieZakupu(db.Model):
    __tablename__ = 'zamowienie_zakupu'
    
    id = db.Column(db.Integer, primary_key=True)
    numer = db.Column(db.String(50), unique=True, nullable=False)
    dostawca_id = db.Column(db.Integer, db.ForeignKey('dostawca.id'), nullable=False)
    data_zamowienia = db.Column(db.DateTime, default=datetime.utcnow)
    data_dostawy_planowana = db.Column(db.DateTime)
    data_dostawy_rzeczywista = db.Column(db.DateTime)
    status = db.Column(Enum(StatusZamowieniaZakupu), default=StatusZamowieniaZakupu.NOWE)
    wartosc_netto = db.Column(db.Numeric(10, 2), default=0)
    uwagi = db.Column(db.Text)
    
    # Relacje
    pozycje = db.relationship('PozycjaZamowieniaZakupu', secondary=pozycje_zamowienia_zakupu,
                             backref=db.backref('zamowienia_zakupu', lazy=True))
    
    def oblicz_wartosc(self):
        """Oblicza wartość zamówienia zakupu"""
        self.wartosc_netto = sum(p.wartosc_netto for p in self.pozycje)
    
    def zmien_status(self, nowy_status):
        """Zmienia status zamówienia zakupu"""
        self.status = nowy_status
        if nowy_status == StatusZamowieniaZakupu.DOSTARCZONE:
            self.data_dostawy_rzeczywista = datetime.utcnow()
    
    def __repr__(self):
        return f'<ZamowienieZakupu {self.numer}>'

# Klasa PozycjaZamowieniaZakupu
class PozycjaZamowieniaZakupu(db.Model):
    __tablename__ = 'pozycja_zamowienia_zakupu'
    
    id = db.Column(db.Integer, primary_key=True)
    produkt_id = db.Column(db.Integer, db.ForeignKey('produkt.id'), nullable=False)
    ilosc = db.Column(db.Integer, nullable=False)
    cena_jednostkowa = db.Column(db.Numeric(10, 2), nullable=False)
    wartosc_netto = db.Column(db.Numeric(10, 2))
    
    # Relacja do produktu
    produkt_rel = db.relationship('Produkt', backref='pozycje_zamowien_zakupu')
    
    def oblicz_wartosc(self):
        """Oblicza wartość pozycji"""
        self.wartosc_netto = self.ilosc * self.cena_jednostkowa
    
    def __repr__(self):
        return f'<PozycjaZamowieniaZakupu {self.id}>'

# Klasa DokumentMagazynowy
class DokumentMagazynowy(db.Model):
    __tablename__ = 'dokument_magazynowy'
    
    id = db.Column(db.Integer, primary_key=True)
    numer = db.Column(db.String(50), unique=True, nullable=False)
    typ = db.Column(Enum(TypDokumentu), nullable=False)
    data_wystawienia = db.Column(db.DateTime, default=datetime.utcnow)
    dostawca_id = db.Column(db.Integer, db.ForeignKey('dostawca.id'))
    zamowienie_id = db.Column(db.Integer, db.ForeignKey('zamowienie.id'))
    uwagi = db.Column(db.Text)
    
    # Relacje
    pozycje = db.relationship('PozycjaDokumentu', backref='dokument', lazy=True)
    dostawca_rel = db.relationship('Dostawca', backref='dokumenty')
    zamowienie_rel = db.relationship('Zamowienie', backref='dokumenty_wz')
    
    def __repr__(self):
        return f'<DokumentMagazynowy {self.numer} - {self.typ.value}>'

# Klasa PozycjaDokumentu
class PozycjaDokumentu(db.Model):
    __tablename__ = 'pozycja_dokumentu'
    
    id = db.Column(db.Integer, primary_key=True)
    dokument_id = db.Column(db.Integer, db.ForeignKey('dokument_magazynowy.id'), nullable=False)
    produkt_id = db.Column(db.Integer, db.ForeignKey('produkt.id'), nullable=False)
    ilosc = db.Column(db.Integer, nullable=False)
    
    def __repr__(self):
        return f'<PozycjaDokumentu {self.id}>'

# Klasa Faktura
class Faktura(db.Model):
    __tablename__ = 'faktura'
    
    id = db.Column(db.Integer, primary_key=True)
    numer = db.Column(db.String(50), unique=True, nullable=False)
    klient_id = db.Column(db.Integer, db.ForeignKey('klient.id'), nullable=False)
    zamowienie_id = db.Column(db.Integer, db.ForeignKey('zamowienie.id'), nullable=False)
    data_wystawienia = db.Column(db.DateTime, default=datetime.utcnow)
    data_sprzedazy = db.Column(db.DateTime, default=datetime.utcnow)
    termin_platnosci = db.Column(db.DateTime)
    wartosc_netto = db.Column(db.Numeric(10, 2), nullable=False)
    wartosc_vat = db.Column(db.Numeric(10, 2), nullable=False)
    wartosc_brutto = db.Column(db.Numeric(10, 2), nullable=False)
    oplacona = db.Column(db.Boolean, default=False)
    
    def generuj_numer(self):
        """Generuje numer faktury w formacie FV/YYYY/MM/NNNN"""
        rok = datetime.now().year
        miesiac = datetime.now().month
        # Zlicz faktury w tym miesiącu
        liczba = Faktura.query.filter(
            db.extract('year', Faktura.data_wystawienia) == rok,
            db.extract('month', Faktura.data_wystawienia) == miesiac
        ).count() + 1
        self.numer = f"FV/{rok}/{miesiac:02d}/{liczba:04d}"
    
    def __repr__(self):
        return f'<Faktura {self.numer}>'

# Klasa Log
class Log(db.Model):
    __tablename__ = 'log'
    
    id = db.Column(db.Integer, primary_key=True)
    uzytkownik_id = db.Column(db.Integer, db.ForeignKey('uzytkownik.id'))
    akcja = db.Column(db.String(200), nullable=False)
    opis = db.Column(db.Text)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    adres_ip = db.Column(db.String(50))
    
    @staticmethod
    def dodaj_log(uzytkownik_id, akcja, opis=None, adres_ip=None):
        """Dodaje wpis do logu"""
        log = Log(
            uzytkownik_id=uzytkownik_id,
            akcja=akcja,
            opis=opis,
            adres_ip=adres_ip
        )
        db.session.add(log)
        db.session.commit()
    
    def __repr__(self):
        return f'<Log {self.akcja} - {self.data}>'