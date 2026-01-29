#!/usr/bin/env python3
"""
Skrypt inicjalizujący bazę danych testowymi danymi
"""
from app import create_app, db
from app.models import (Uzytkownik, RolaUzytkownika, Produkt, StanMagazynowy, 
                        Klient, Dostawca)
from decimal import Decimal

def init_database():
    app = create_app()
    
    with app.app_context():
        # Usunięcie i utworzenie tabel
        print("Tworzenie tabel...")
        db.drop_all()
        db.create_all()
        
        # Dodawanie użytkowników testowych
        print("Dodawanie użytkowników...")
        users = [
            {
                'login': 'admin',
                'imie': 'Jan',
                'nazwisko': 'Kowalski',
                'email': 'admin@bhp.pl',
                'rola': RolaUzytkownika.ADMINISTRATOR,
                'haslo': 'admin123'
            },
            {
                'login': 'magazyn',
                'imie': 'Piotr',
                'nazwisko': 'Nowak',
                'email': 'magazyn@bhp.pl',
                'rola': RolaUzytkownika.MAGAZYNIER,
                'haslo': 'magazyn123'
            },
            {
                'login': 'sprzedaz',
                'imie': 'Anna',
                'nazwisko': 'Wiśniewska',
                'email': 'sprzedaz@bhp.pl',
                'rola': RolaUzytkownika.SPRZEDAWCA,
                'haslo': 'sprzedaz123'
            },
            {
                'login': 'kierownik',
                'imie': 'Marek',
                'nazwisko': 'Zieliński',
                'email': 'kierownik@bhp.pl',
                'rola': RolaUzytkownika.KIEROWNIK,
                'haslo': 'kierownik123'
            }
        ]
        
        for user_data in users:
            haslo = user_data.pop('haslo')
            user = Uzytkownik(**user_data)
            user.ustaw_haslo(haslo)
            db.session.add(user)
        
        # Dodawanie dostawców
        print("Dodawanie dostawców...")
        dostawcy = [
            {
                'nazwa': 'BHP Plus Sp. z o.o.',
                'nip': '1234567890',
                'adres': 'ul. Bezpieczna 10',
                'telefon': '123456789',
                'email': 'kontakt@bhpplus.pl',
                'kontakt_osoba': 'Krzysztof Nowicki'
            },
            {
                'nazwa': 'Odziez Robocza S.A.',
                'nip': '9876543210',
                'adres': 'ul. Przemysłowa 25',
                'telefon': '987654321',
                'email': 'zamowienia@odziezrobocza.pl',
                'kontakt_osoba': 'Ewa Kowalczyk'
            }
        ]
        
        for dostawca_data in dostawcy:
            dostawca = Dostawca(**dostawca_data)
            db.session.add(dostawca)
        
        # Dodawanie klientów
        print("Dodawanie klientów...")
        klienci = [
            {
                'nazwa': 'Firma Sprzątająca ABC',
                'nip': '1111111111',
                'adres': 'ul. Czysta 5',
                'kod_pocztowy': '00-001',
                'miasto': 'Warszawa',
                'telefon': '111222333',
                'email': 'kontakt@abc-sprzatanie.pl'
            },
            {
                'nazwa': 'Hotel Grand Sp. z o.o.',
                'nip': '2222222222',
                'adres': 'ul. Hotelowa 100',
                'kod_pocztowy': '00-002',
                'miasto': 'Kraków',
                'telefon': '444555666',
                'email': 'zamowienia@hotelgrand.pl'
            },
            {
                'nazwa': 'Zakłady Produkcyjne XYZ',
                'nip': '3333333333',
                'adres': 'ul. Fabryczna 50',
                'kod_pocztowy': '61-001',
                'miasto': 'Poznań',
                'telefon': '777888999',
                'email': 'bhp@xyz.com.pl'
            }
        ]
        
        for klient_data in klienci:
            klient = Klient(**klient_data)
            db.session.add(klient)
        
        # Dodawanie produktów
        print("Dodawanie produktów...")
        produkty = [
            # Odzież robocza
            {'kod': 'ODZ001', 'nazwa': 'Kurtka robocza zimowa', 'kategoria': 'Odzież robocza', 
             'jednostka': 'szt', 'cena_jednostkowa': Decimal('150.00'), 'stan_minimalny': 20},
            {'kod': 'ODZ002', 'nazwa': 'Spodnie ogrodniczki', 'kategoria': 'Odzież robocza', 
             'jednostka': 'szt', 'cena_jednostkowa': Decimal('80.00'), 'stan_minimalny': 30},
            {'kod': 'ODZ003', 'nazwa': 'Kamizelka odblaskowa', 'kategoria': 'Odzież robocza', 
             'jednostka': 'szt', 'cena_jednostkowa': Decimal('25.00'), 'stan_minimalny': 50},
            {'kod': 'ODZ004', 'nazwa': 'Bluza polarowa', 'kategoria': 'Odzież robocza', 
             'jednostka': 'szt', 'cena_jednostkowa': Decimal('60.00'), 'stan_minimalny': 25},
            
            # Obuwie
            {'kod': 'OBU001', 'nazwa': 'Buty robocze S3', 'kategoria': 'Obuwie', 
             'jednostka': 'para', 'cena_jednostkowa': Decimal('120.00'), 'stan_minimalny': 15},
            {'kod': 'OBU002', 'nazwa': 'Kalosze gumowe', 'kategoria': 'Obuwie', 
             'jednostka': 'para', 'cena_jednostkowa': Decimal('45.00'), 'stan_minimalny': 20},
            
            # Rękawice
            {'kod': 'REK001', 'nazwa': 'Rękawice robocze bawełniane', 'kategoria': 'Rękawice', 
             'jednostka': 'para', 'cena_jednostkowa': Decimal('5.00'), 'stan_minimalny': 100},
            {'kod': 'REK002', 'nazwa': 'Rękawice gumowe', 'kategoria': 'Rękawice', 
             'jednostka': 'para', 'cena_jednostkowa': Decimal('8.00'), 'stan_minimalny': 80},
            {'kod': 'REK003', 'nazwa': 'Rękawice skórzane', 'kategoria': 'Rękawice', 
             'jednostka': 'para', 'cena_jednostkowa': Decimal('15.00'), 'stan_minimalny': 40},
            
            # Środki czystości
            {'kod': 'CZY001', 'nazwa': 'Płyn do mycia podłóg 5L', 'kategoria': 'Środki czystości', 
             'jednostka': 'szt', 'cena_jednostkowa': Decimal('35.00'), 'stan_minimalny': 30},
            {'kod': 'CZY002', 'nazwa': 'Detergent uniwersalny 1L', 'kategoria': 'Środki czystości', 
             'jednostka': 'szt', 'cena_jednostkowa': Decimal('12.00'), 'stan_minimalny': 50},
            {'kod': 'CZY003', 'nazwa': 'Pasta do czyszczenia', 'kategoria': 'Środki czystości', 
             'jednostka': 'szt', 'cena_jednostkowa': Decimal('8.00'), 'stan_minimalny': 40},
            {'kod': 'CZY004', 'nazwa': 'Worki na śmieci 120L', 'kategoria': 'Środki czystości', 
             'jednostka': 'op', 'cena_jednostkowa': Decimal('25.00'), 'stan_minimalny': 20},
            
            # Akcesoria
            {'kod': 'AKC001', 'nazwa': 'Mop bawełniany', 'kategoria': 'Akcesoria', 
             'jednostka': 'szt', 'cena_jednostkowa': Decimal('18.00'), 'stan_minimalny': 25},
            {'kod': 'AKC002', 'nazwa': 'Wiadro plastikowe 10L', 'kategoria': 'Akcesoria', 
             'jednostka': 'szt', 'cena_jednostkowa': Decimal('15.00'), 'stan_minimalny': 30},
            {'kod': 'AKC003', 'nazwa': 'Szczotka do zamiatania', 'kategoria': 'Akcesoria', 
             'jednostka': 'szt', 'cena_jednostkowa': Decimal('12.00'), 'stan_minimalny': 20},
        ]
        
        for produkt_data in produkty:
            produkt = Produkt(**produkt_data)
            db.session.add(produkt)
            db.session.flush()
            
            # Tworzenie stanu magazynowego
            import random
            stan = StanMagazynowy(
                produkt_id=produkt.id,
                ilosc_dostepna=random.randint(5, 100),
                ilosc_zarezerwowana=0,
                lokalizacja=f"Regal-{random.randint(1, 10)}-{random.randint(1, 5)}"
            )
            db.session.add(stan)
        
        db.session.commit()
        print("\n✓ Baza danych została zainicjowana!")
        print("\nUżytkownicy testowi:")
        print("  Administrator: login=admin, hasło=admin123")
        print("  Magazynier:    login=magazyn, hasło=magazyn123")
        print("  Sprzedawca:    login=sprzedaz, hasło=sprzedaz123")
        print("  Kierownik:     login=kierownik, hasło=kierownik123")
        print(f"\nDodano {len(produkty)} produktów")
        print(f"Dodano {len(klienci)} klientów")
        print(f"Dodano {len(dostawcy)} dostawców")

if __name__ == '__main__':
    init_database()