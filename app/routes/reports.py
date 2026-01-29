from flask import Blueprint, render_template, request, g
from app.models import (db, Zamowienie, StanMagazynowy, Produkt, Faktura, 
                        DokumentMagazynowy, TypDokumentu, PozycjaZamowienia)
from app.routes.auth import login_required, role_required
from datetime import datetime, timedelta
from sqlalchemy import func

bp = Blueprint('reports', __name__, url_prefix='/reports')

# UC10: Generowanie raportów
@bp.route('/')
@role_required('Kierownik', 'Administrator')
def index():
    """Strona główna raportów"""
    return render_template('reports/index.html')

@bp.route('/sales')
@role_required('Kierownik', 'Administrator')
def sales_report():
    """Raport sprzedaży"""
    # Pobieranie parametrów
    data_od = request.args.get('data_od', '')
    data_do = request.args.get('data_do', '')
    
    # Domyślnie: ostatni miesiąc
    if not data_od:
        data_od = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not data_do:
        data_do = datetime.now().strftime('%Y-%m-%d')
    
    # Konwersja na datetime
    dt_od = datetime.strptime(data_od, '%Y-%m-%d')
    dt_do = datetime.strptime(data_do, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    
    # Zapytanie o zamówienia
    zamowienia = Zamowienie.query.filter(
        Zamowienie.data_zamowienia.between(dt_od, dt_do)
    ).all()
    
    # Obliczenia
    suma_netto = sum(z.wartosc_netto or 0 for z in zamowienia)
    suma_brutto = sum(z.wartosc_brutto or 0 for z in zamowienia)
    liczba_zamowien = len(zamowienia)
    
    # Sprzedaż według kategorii - uproszczone
    sprzedaz_kategorie = []
    try:
        # Pobierz wszystkie pozycje zamówień z danego okresu
        for zamowienie in zamowienia:
            for pozycja in zamowienie.pozycje:
                kategoria = pozycja.produkt_rel.kategoria if pozycja.produkt_rel else 'Brak'
                # Znajdź lub dodaj kategorię
                found = False
                for item in sprzedaz_kategorie:
                    if item[0] == kategoria:
                        item[1] += float(pozycja.wartosc_netto or 0)
                        found = True
                        break
                if not found:
                    sprzedaz_kategorie.append([kategoria, float(pozycja.wartosc_netto or 0)])
    except Exception as e:
        print(f"Błąd przy kategorii: {e}")
        sprzedaz_kategorie = []
    
    return render_template('reports/sales_report.html',
                         zamowienia=zamowienia,
                         suma_netto=suma_netto,
                         suma_brutto=suma_brutto,
                         liczba_zamowien=liczba_zamowien,
                         sprzedaz_kategorie=sprzedaz_kategorie,
                         data_od=data_od,
                         data_do=data_do)

# UC11: Analiza stanów magazynowych
@bp.route('/inventory')
@role_required('Kierownik', 'Magazynier', 'Administrator')
def inventory_report():
    """Raport stanów magazynowych"""
    kategoria = request.args.get('kategoria', '')
    tylko_niskie = request.args.get('tylko_niskie', '') == 'on'
    
    query = StanMagazynowy.query.join(Produkt)
    
    if kategoria:
        query = query.filter(Produkt.kategoria == kategoria)
    
    stany = query.all()
    
    if tylko_niskie:
        stany = [s for s in stany if s.czy_niski_stan()]
    
    # Wartość magazynu
    wartosc_magazynu = sum(
        float(s.ilosc_dostepna) * float(s.produkt.cena_jednostkowa) 
        for s in stany
    )
    
    # Produkty o niskim stanie
    niskie_stany = [s for s in stany if s.czy_niski_stan()]
    
    kategorie = db.session.query(Produkt.kategoria).distinct().all()
    kategorie = [k[0] for k in kategorie if k[0]]
    
    return render_template('reports/inventory_report.html',
                         stany=stany,
                         niskie_stany=niskie_stany,
                         wartosc_magazynu=wartosc_magazynu,
                         kategorie=kategorie,
                         aktywna_kategoria=kategoria)

@bp.route('/product-rotation')
@role_required('Kierownik', 'Administrator')
def product_rotation():
    """Raport rotacji produktów"""
    data_od = request.args.get('data_od', '')
    data_do = request.args.get('data_do', '')
    
    if not data_od:
        data_od = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    if not data_do:
        data_do = datetime.now().strftime('%Y-%m-%d')
    
    dt_od = datetime.strptime(data_od, '%Y-%m-%d')
    dt_do = datetime.strptime(data_do, '%Y-%m-%d')
    
    # Uproszczone zapytanie - zbieramy dane ręcznie
    produkty_rotacja = []
    
    # Pobierz wszystkie zamówienia z okresu
    zamowienia = Zamowienie.query.filter(
        Zamowienie.data_zamowienia.between(dt_od, dt_do)
    ).all()
    
    # Zlicz sprzedaż dla każdego produktu
    sprzedaz_dict = {}
    for zamowienie in zamowienia:
        for pozycja in zamowienie.pozycje:
            produkt_id = pozycja.produkt_id
            if produkt_id not in sprzedaz_dict:
                sprzedaz_dict[produkt_id] = {
                    'produkt': pozycja.produkt_rel,
                    'ilosc': 0
                }
            sprzedaz_dict[produkt_id]['ilosc'] += pozycja.ilosc
    
    # Konwertuj do listy i sortuj
    produkty_rotacja = [
        (data['produkt'], data['ilosc']) 
        for data in sprzedaz_dict.values()
    ]
    produkty_rotacja.sort(key=lambda x: x[1], reverse=True)
    
    # Dodaj produkty które nie były sprzedawane
    wszystkie_produkty = Produkt.query.filter_by(aktywny=True).all()
    sprzedane_ids = set(sprzedaz_dict.keys())
    
    for produkt in wszystkie_produkty:
        if produkt.id not in sprzedane_ids:
            produkty_rotacja.append((produkt, 0))
    
    return render_template('reports/product_rotation.html',
                         produkty_rotacja=produkty_rotacja,
                         data_od=data_od,
                         data_do=data_do)

@bp.route('/documents')
@role_required('Kierownik', 'Administrator')
def documents_report():
    """Raport dokumentów magazynowych"""
    typ = request.args.get('typ', '')
    data_od = request.args.get('data_od', '')
    data_do = request.args.get('data_do', '')
    
    if not data_od:
        data_od = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not data_do:
        data_do = datetime.now().strftime('%Y-%m-%d')
    
    dt_od = datetime.strptime(data_od, '%Y-%m-%d')
    dt_do = datetime.strptime(data_do, '%Y-%m-%d')
    
    query = DokumentMagazynowy.query.filter(
        DokumentMagazynowy.data_wystawienia.between(dt_od, dt_do)
    )
    
    if typ:
        query = query.filter_by(typ=TypDokumentu[typ])
    
    dokumenty = query.order_by(DokumentMagazynowy.data_wystawienia.desc()).all()
    
    return render_template('reports/documents_report.html',
                         dokumenty=dokumenty,
                         data_od=data_od,
                         data_do=data_do,
                         typ_filtr=typ)

@bp.route('/invoices')
@role_required('Kierownik', 'Administrator')
def invoices_report():
    """Raport faktur"""
    data_od = request.args.get('data_od', '')
    data_do = request.args.get('data_do', '')
    
    if not data_od:
        data_od = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not data_do:
        data_do = datetime.now().strftime('%Y-%m-%d')
    
    dt_od = datetime.strptime(data_od, '%Y-%m-%d')
    dt_do = datetime.strptime(data_do, '%Y-%m-%d')
    
    faktury = Faktura.query.filter(
        Faktura.data_wystawienia.between(dt_od, dt_do)
    ).all()
    
    suma_netto = sum(f.wartosc_netto for f in faktury)
    suma_brutto = sum(f.wartosc_brutto for f in faktury)
    liczba_faktur = len(faktury)
    faktury_oplacone = sum(1 for f in faktury if f.oplacona)
    
    return render_template('reports/invoices_report.html',
                         faktury=faktury,
                         suma_netto=suma_netto,
                         suma_brutto=suma_brutto,
                         liczba_faktur=liczba_faktur,
                         faktury_oplacone=faktury_oplacone,
                         data_od=data_od,
                         data_do=data_do)