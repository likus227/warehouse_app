from flask import Blueprint, render_template, redirect, url_for, flash, request, g
from app.models import (db, DokumentMagazynowy, PozycjaDokumentu, Produkt, 
                        StanMagazynowy, Dostawca, TypDokumentu, Log, Zamowienie)
from app.routes.auth import login_required, role_required
from datetime import datetime

bp = Blueprint('warehouse', __name__, url_prefix='/warehouse')

@bp.route('/')
@login_required
def index():
    """Strona główna magazynu"""
    stany = StanMagazynowy.query.join(Produkt).filter(
        Produkt.aktywny == True
    ).all()
    
    niskie_stany = [s for s in stany if s.czy_niski_stan()]
    
    return render_template('warehouse/index.html', 
                         stany=stany, 
                         niskie_stany=niskie_stany)

# UC4: Rejestrowanie przyjęcia towaru (PZ)
@bp.route('/pz/add', methods=['GET', 'POST'])
@role_required('Magazynier', 'Administrator')
def pz_add():
    """Dodawanie dokumentu przyjęcia (PZ)"""
    if request.method == 'POST':
        dostawca_id = request.form.get('dostawca_id')
        pozycje_data = request.form.getlist('produkt_id[]')
        
        if not pozycje_data:
            flash('Dodaj co najmniej jedną pozycję do dokumentu.', 'warning')
            return render_template('warehouse/pz_form.html', 
                                 dostawcy=Dostawca.query.filter_by(aktywny=True).all(),
                                 produkty=Produkt.query.filter_by(aktywny=True).all())
        
        # Generowanie numeru dokumentu
        rok = datetime.now().year
        liczba = DokumentMagazynowy.query.filter_by(typ=TypDokumentu.PRZYJECIE).count() + 1
        numer = f"PZ/{rok}/{liczba:05d}"
        
        dokument = DokumentMagazynowy(
            numer=numer,
            typ=TypDokumentu.PRZYJECIE,
            dostawca_id=dostawca_id,
            uwagi=request.form.get('uwagi')
        )
        
        db.session.add(dokument)
        db.session.flush()
        
        # Dodawanie pozycji
        for i, produkt_id in enumerate(pozycje_data):
            ilosc = int(request.form.getlist('ilosc[]')[i])
            
            pozycja = PozycjaDokumentu(
                dokument_id=dokument.id,
                produkt_id=int(produkt_id),
                ilosc=ilosc
            )
            db.session.add(pozycja)
            
            # Aktualizacja stanu magazynowego
            stan = StanMagazynowy.query.filter_by(produkt_id=int(produkt_id)).first()
            if stan:
                stan.aktualizuj_stan(ilosc, 'dodaj')
        
        db.session.commit()
        
        Log.dodaj_log(g.user.id, 'Przyjęcie towaru', 
                     f'Utworzono dokument PZ: {dokument.numer}')
        
        flash(f'Dokument {dokument.numer} został utworzony.', 'success')
        return redirect(url_for('warehouse.pz_detail', dokument_id=dokument.id))
    
    dostawcy = Dostawca.query.filter_by(aktywny=True).all()
    produkty = Produkt.query.filter_by(aktywny=True).order_by(Produkt.nazwa).all()
    
    return render_template('warehouse/pz_form.html', 
                         dostawcy=dostawcy, 
                         produkty=produkty)

# UC5: Rejestrowanie wydania towaru (WZ)
@bp.route('/wz/add', methods=['GET', 'POST'])
@role_required('Magazynier', 'Administrator')
def wz_add():
    """Dodawanie dokumentu wydania (WZ)"""
    if request.method == 'POST':
        zamowienie_id = request.form.get('zamowienie_id')
        pozycje_data = request.form.getlist('produkt_id[]')
        
        if not pozycje_data:
            flash('Dodaj co najmniej jedną pozycję do dokumentu.', 'warning')
            return render_template('warehouse/wz_form.html',
                                 zamowienia=Zamowienie.query.filter_by(status='GOTOWE').all(),
                                 produkty=Produkt.query.filter_by(aktywny=True).all())
        
        # Generowanie numeru dokumentu
        rok = datetime.now().year
        liczba = DokumentMagazynowy.query.filter_by(typ=TypDokumentu.WYDANIE).count() + 1
        numer = f"WZ/{rok}/{liczba:05d}"
        
        dokument = DokumentMagazynowy(
            numer=numer,
            typ=TypDokumentu.WYDANIE,
            zamowienie_id=zamowienie_id,
            uwagi=request.form.get('uwagi')
        )
        
        db.session.add(dokument)
        db.session.flush()
        
        # Sprawdzenie dostępności i dodawanie pozycji
        for i, produkt_id in enumerate(pozycje_data):
            ilosc = int(request.form.getlist('ilosc[]')[i])
            
            stan = StanMagazynowy.query.filter_by(produkt_id=int(produkt_id)).first()
            
            if not stan or stan.ilosc_dostepna < ilosc:
                db.session.rollback()
                produkt = Produkt.query.get(int(produkt_id))
                flash(f'Brak wystarczającej ilości produktu: {produkt.nazwa}', 'danger')
                return redirect(url_for('warehouse.wz_add'))
            
            pozycja = PozycjaDokumentu(
                dokument_id=dokument.id,
                produkt_id=int(produkt_id),
                ilosc=ilosc
            )
            db.session.add(pozycja)
            
            # Aktualizacja stanu magazynowego
            stan.aktualizuj_stan(ilosc, 'odejmij')
        
        # Aktualizacja statusu zamówienia
        if zamowienie_id:
            zamowienie = Zamowienie.query.get(zamowienie_id)
            zamowienie.zmien_status('WYSLANE')
        
        db.session.commit()
        
        Log.dodaj_log(g.user.id, 'Wydanie towaru', 
                     f'Utworzono dokument WZ: {dokument.numer}')
        
        flash(f'Dokument {dokument.numer} został utworzony.', 'success')
        return redirect(url_for('warehouse.wz_detail', dokument_id=dokument.id))
    
    zamowienia = Zamowienie.query.filter(
        Zamowienie.status.in_(['GOTOWE', 'W_REALIZACJI'])
    ).all()
    produkty = Produkt.query.filter_by(aktywny=True).order_by(Produkt.nazwa).all()
    
    return render_template('warehouse/wz_form.html', 
                         zamowienia=zamowienia,
                         produkty=produkty)

@bp.route('/documents')
@login_required
def documents_list():
    """Lista dokumentów magazynowych"""
    typ = request.args.get('typ', '')
    page = request.args.get('page', 1, type=int)
    
    query = DokumentMagazynowy.query
    
    if typ:
        query = query.filter_by(typ=TypDokumentu[typ])
    
    dokumenty = query.order_by(DokumentMagazynowy.data_wystawienia.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('warehouse/documents_list.html', 
                         dokumenty=dokumenty,
                         typ_filtr=typ)

@bp.route('/pz/<int:dokument_id>')
@login_required
def pz_detail(dokument_id):
    """Szczegóły dokumentu PZ"""
    dokument = DokumentMagazynowy.query.get_or_404(dokument_id)
    return render_template('warehouse/pz_detail.html', dokument=dokument)

@bp.route('/wz/<int:dokument_id>')
@login_required
def wz_detail(dokument_id):
    """Szczegóły dokumentu WZ"""
    dokument = DokumentMagazynowy.query.get_or_404(dokument_id)
    return render_template('warehouse/wz_detail.html', dokument=dokument)

@bp.route('/suppliers')
@login_required
def suppliers_list():
    """Lista dostawców"""
    dostawcy = Dostawca.query.all()
    return render_template('warehouse/suppliers_list.html', dostawcy=dostawcy)

@bp.route('/suppliers/add', methods=['GET', 'POST'])
@role_required('Administrator', 'Kierownik')
def supplier_add():
    """Dodawanie dostawcy"""
    if request.method == 'POST':
        dostawca = Dostawca(
            nazwa=request.form.get('nazwa'),
            nip=request.form.get('nip'),
            adres=request.form.get('adres'),
            telefon=request.form.get('telefon'),
            email=request.form.get('email'),
            kontakt_osoba=request.form.get('kontakt_osoba'),
            aktywny=True
        )
        
        db.session.add(dostawca)
        db.session.commit()
        
        Log.dodaj_log(g.user.id, 'Dodanie dostawcy', 
                     f'Dodano dostawcę: {dostawca.nazwa}')
        
        flash(f'Dostawca {dostawca.nazwa} został dodany.', 'success')
        return redirect(url_for('warehouse.suppliers_list'))
    
    return render_template('warehouse/supplier_form.html')

@bp.route('/suppliers/<int:dostawca_id>/edit', methods=['GET', 'POST'])
@role_required('Administrator', 'Kierownik')
def supplier_edit(dostawca_id):
    """Edycja dostawcy"""
    dostawca = Dostawca.query.get_or_404(dostawca_id)
    
    if request.method == 'POST':
        dostawca.nazwa = request.form.get('nazwa')
        dostawca.nip = request.form.get('nip')
        dostawca.adres = request.form.get('adres')
        dostawca.telefon = request.form.get('telefon')
        dostawca.email = request.form.get('email')
        dostawca.kontakt_osoba = request.form.get('kontakt_osoba')
        dostawca.aktywny = request.form.get('aktywny') == 'on'
        
        db.session.commit()
        
        Log.dodaj_log(g.user.id, 'Edycja dostawcy', 
                     f'Edytowano dostawcę: {dostawca.nazwa}')
        
        flash(f'Dostawca {dostawca.nazwa} został zaktualizowany.', 'success')
        return redirect(url_for('warehouse.suppliers_list'))
    
    return render_template('warehouse/supplier_form.html', dostawca=dostawca)