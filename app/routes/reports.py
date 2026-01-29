from flask import Blueprint, render_template, request, g
from app.models import (db, Zamowienie, StanMagazynowy, Produkt, Faktura, 
                        DokumentMagazynowy, TypDokumentu)
from app.routes.auth import login_required, role_required
from datetime import datetime, timedelta
from sqlalchemy import func, extract

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
    
    # Sprzedaż według kategorii
    sprzedaz_kategorie = db.session.query(
        Produkt.kategoria,
        func.sum(db.cast(db.literal_column('pozycja_zamowienia.wartosc_netto'), db.Numeric)).label('wartosc')
    ).join(
        db.literal_column('pozycja_zamowienia'), 
        Produkt.id == db.literal_column('pozycja_zamowienia.produkt_id')
    ).join(
        db.literal_column('pozycje_zamowienia'),
        db.literal_column('pozycja_zamowienia.id') == db.literal_column('pozycje_zamowienia.pozycja_id')
    ).join(
        Zamowienie,
        Zamowienie.id == db.literal_column('pozycje_zamowienia.zamowienie_id')
    ).filter(
        Zamowienie.data_zamowienia.between(dt_od, dt_do)
    ).group_by(Produkt.kategoria).all()
    
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
        s.ilosc_dostepna * s.produkt.cena_jednostkowa 
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
    
    # Produkty z ilością sprzedaży
    produkty_rotacja = db.session.query(
        Produkt,
        func.coalesce(func.sum(db.literal_column('pozycja_zamowienia.ilosc')), 0).label('ilosc_sprzedana')
    ).outerjoin(
        db.literal_column('pozycja_zamowienia'),
        Produkt.id == db.literal_column('pozycja_zamowienia.produkt_id')
    ).outerjoin(
        db.literal_column('pozycje_zamowienia'),
        db.literal_column('pozycja_zamowienia.id') == db.literal_column('pozycje_zamowienia.pozycja_id')
    ).outerjoin(
        Zamowienie,
        Zamowienie.id == db.literal_column('pozycje_zamowienia.zamowienie_id')
    ).filter(
        db.or_(
            Zamowienie.data_zamowienia.between(dt_od, dt_do),
            Zamowienie.data_zamowienia.is_(None)
        )
    ).group_by(Produkt.id).order_by(
        func.sum(db.literal_column('pozycja_zamowienia.ilosc')).desc()
    ).all()
    
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