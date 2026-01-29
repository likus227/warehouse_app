from flask import Blueprint, render_template, redirect, url_for, flash, request, g
from app.models import (db, Zamowienie, PozycjaZamowienia, ZamowienieZakupu, 
                        PozycjaZamowieniaZakupu, Klient, Dostawca, Produkt, 
                        Faktura, StatusZamowienia, StatusZamowieniaZakupu, Log)
from app.routes.auth import login_required, role_required
from datetime import datetime, timedelta
from decimal import Decimal

bp = Blueprint('orders', __name__, url_prefix='/orders')

# UC6: Rejestrowanie zamówienia klienta
@bp.route('/customer/add', methods=['GET', 'POST'])
@role_required('Sprzedawca', 'Administrator')
def customer_order_add():
    """Dodawanie zamówienia klienta"""
    if request.method == 'POST':
        klient_id = request.form.get('klient_id')
        pozycje_data = request.form.getlist('produkt_id[]')
        
        if not pozycje_data:
            flash('Dodaj co najmniej jedną pozycję do zamówienia.', 'warning')
            return render_template('orders/customer_order_form.html',
                                 klienci=Klient.query.filter_by(aktywny=True).all(),
                                 produkty=Produkt.query.filter_by(aktywny=True).all())
        
        # Generowanie numeru zamówienia
        rok = datetime.now().year
        liczba = Zamowienie.query.filter(
            db.extract('year', Zamowienie.data_zamowienia) == rok
        ).count() + 1
        numer = f"ZAM/{rok}/{liczba:05d}"
        
        zamowienie = Zamowienie(
            numer=numer,
            klient_id=klient_id,
            status=StatusZamowienia.NOWE,
            uwagi=request.form.get('uwagi')
        )
        
        db.session.add(zamowienie)
        db.session.flush()
        
        # Dodawanie pozycji
        for i, produkt_id in enumerate(pozycje_data):
            produkt = Produkt.query.get(int(produkt_id))
            ilosc = int(request.form.getlist('ilosc[]')[i])
            
            pozycja = PozycjaZamowienia(
                produkt_id=int(produkt_id),
                ilosc=ilosc,
                cena_jednostkowa=produkt.cena_jednostkowa
            )
            pozycja.oblicz_wartosc()
            
            db.session.add(pozycja)
            db.session.flush()
            
            zamowienie.pozycje.append(pozycja)
        
        zamowienie.oblicz_wartosc()
        db.session.commit()
        
        Log.dodaj_log(g.user.id, 'Nowe zamówienie', 
                     f'Utworzono zamówienie: {zamowienie.numer}')
        
        flash(f'Zamówienie {zamowienie.numer} zostało utworzone.', 'success')
        return redirect(url_for('orders.customer_order_detail', zamowienie_id=zamowienie.id))
    
    klienci = Klient.query.filter_by(aktywny=True).order_by(Klient.nazwa).all()
    produkty = Produkt.query.filter_by(aktywny=True).order_by(Produkt.nazwa).all()
    
    return render_template('orders/customer_order_form.html', 
                         klienci=klienci,
                         produkty=produkty)

@bp.route('/customer')
@login_required
def customer_orders_list():
    """Lista zamówień klientów"""
    status = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    
    query = Zamowienie.query
    
    if status:
        query = query.filter_by(status=StatusZamowienia[status])
    
    zamowienia = query.order_by(Zamowienie.data_zamowienia.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('orders/customer_orders_list.html', 
                         zamowienia=zamowienia,
                         status_filtr=status,
                         statusy=StatusZamowienia)

@bp.route('/customer/<int:zamowienie_id>')
@login_required
def customer_order_detail(zamowienie_id):
    """Szczegóły zamówienia klienta"""
    zamowienie = Zamowienie.query.get_or_404(zamowienie_id)
    return render_template('orders/customer_order_detail.html', zamowienie=zamowienie)

# UC7: Realizacja zamówienia klienta
@bp.route('/customer/<int:zamowienie_id>/realize', methods=['POST'])
@role_required('Magazynier', 'Administrator')
def customer_order_realize(zamowienie_id):
    """Realizacja zamówienia - kompletacja"""
    zamowienie = Zamowienie.query.get_or_404(zamowienie_id)
    
    if zamowienie.status == StatusZamowienia.NOWE:
        zamowienie.zmien_status(StatusZamowienia.W_REALIZACJI)
        db.session.commit()
        
        flash(f'Zamówienie {zamowienie.numer} jest w realizacji.', 'success')
    
    return redirect(url_for('orders.customer_order_detail', zamowienie_id=zamowienie_id))

@bp.route('/customer/<int:zamowienie_id>/complete', methods=['POST'])
@role_required('Magazynier', 'Administrator')
def customer_order_complete(zamowienie_id):
    """Oznaczenie zamówienia jako gotowe"""
    zamowienie = Zamowienie.query.get_or_404(zamowienie_id)
    
    # Sprawdzenie czy wszystkie pozycje są skompletowane
    wszystkie_skompletowane = all(p.skompletowane for p in zamowienie.pozycje)
    
    if wszystkie_skompletowane:
        zamowienie.zmien_status(StatusZamowienia.GOTOWE)
        db.session.commit()
        
        Log.dodaj_log(g.user.id, 'Kompletacja zamówienia', 
                     f'Zamówienie {zamowienie.numer} gotowe do wydania')
        
        flash(f'Zamówienie {zamowienie.numer} jest gotowe do wydania.', 'success')
    else:
        flash('Nie wszystkie pozycje są skompletowane.', 'warning')
    
    return redirect(url_for('orders.customer_order_detail', zamowienie_id=zamowienie_id))

@bp.route('/customer/<int:zamowienie_id>/position/<int:pozycja_id>/toggle')
@role_required('Magazynier', 'Administrator')
def toggle_position(zamowienie_id, pozycja_id):
    """Oznaczenie pozycji jako skompletowanej"""
    pozycja = PozycjaZamowienia.query.get_or_404(pozycja_id)
    pozycja.skompletowane = not pozycja.skompletowane
    db.session.commit()
    
    return redirect(url_for('orders.customer_order_detail', zamowienie_id=zamowienie_id))

# UC8: Wystawianie faktury
@bp.route('/customer/<int:zamowienie_id>/invoice', methods=['GET', 'POST'])
@role_required('Sprzedawca', 'Administrator')
def create_invoice(zamowienie_id):
    """Wystawianie faktury dla zamówienia"""
    zamowienie = Zamowienie.query.get_or_404(zamowienie_id)
    
    if zamowienie.faktura:
        flash('Faktura dla tego zamówienia już istnieje.', 'warning')
        return redirect(url_for('orders.customer_order_detail', zamowienie_id=zamowienie_id))
    
    if request.method == 'POST':
        faktura = Faktura(
            klient_id=zamowienie.klient_id,
            zamowienie_id=zamowienie.id,
            data_sprzedazy=datetime.now(),
            termin_platnosci=datetime.now() + timedelta(days=14),
            wartosc_netto=zamowienie.wartosc_netto,
            wartosc_vat=zamowienie.wartosc_netto * Decimal('0.23'),
            wartosc_brutto=zamowienie.wartosc_brutto
        )
        faktura.generuj_numer()
        
        db.session.add(faktura)
        db.session.commit()
        
        Log.dodaj_log(g.user.id, 'Wystawienie faktury', 
                     f'Wystawiono fakturę: {faktura.numer}')
        
        flash(f'Faktura {faktura.numer} została wystawiona.', 'success')
        return redirect(url_for('orders.invoice_detail', faktura_id=faktura.id))
    
    return render_template('orders/invoice_form.html', zamowienie=zamowienie)

@bp.route('/invoices')
@login_required
def invoices_list():
    """Lista faktur"""
    page = request.args.get('page', 1, type=int)
    
    faktury = Faktura.query.order_by(Faktura.data_wystawienia.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('orders/invoices_list.html', faktury=faktury)

@bp.route('/invoices/<int:faktura_id>')
@login_required
def invoice_detail(faktura_id):
    """Szczegóły faktury"""
    faktura = Faktura.query.get_or_404(faktura_id)
    return render_template('orders/invoice_detail.html', faktura=faktura)

# UC9: Składanie zamówienia do dostawcy
@bp.route('/supplier/add', methods=['GET', 'POST'])
@role_required('Kierownik', 'Administrator')
def supplier_order_add():
    """Dodawanie zamówienia do dostawcy"""
    if request.method == 'POST':
        dostawca_id = request.form.get('dostawca_id')
        pozycje_data = request.form.getlist('produkt_id[]')
        
        if not pozycje_data:
            flash('Dodaj co najmniej jedną pozycję do zamówienia.', 'warning')
            return render_template('orders/supplier_order_form.html',
                                 dostawcy=Dostawca.query.filter_by(aktywny=True).all(),
                                 produkty=Produkt.query.filter_by(aktywny=True).all())
        
        # Generowanie numeru zamówienia
        rok = datetime.now().year
        liczba = ZamowienieZakupu.query.filter(
            db.extract('year', ZamowienieZakupu.data_zamowienia) == rok
        ).count() + 1
        numer = f"ZAK/{rok}/{liczba:05d}"
        
        zamowienie = ZamowienieZakupu(
            numer=numer,
            dostawca_id=dostawca_id,
            data_dostawy_planowana=datetime.strptime(
                request.form.get('data_dostawy'), '%Y-%m-%d'
            ) if request.form.get('data_dostawy') else None,
            status=StatusZamowieniaZakupu.NOWE,
            uwagi=request.form.get('uwagi')
        )
        
        db.session.add(zamowienie)
        db.session.flush()
        
        # Dodawanie pozycji
        for i, produkt_id in enumerate(pozycje_data):
            ilosc = int(request.form.getlist('ilosc[]')[i])
            cena = Decimal(request.form.getlist('cena[]')[i])
            
            pozycja = PozycjaZamowieniaZakupu(
                produkt_id=int(produkt_id),
                ilosc=ilosc,
                cena_jednostkowa=cena
            )
            pozycja.oblicz_wartosc()
            
            db.session.add(pozycja)
            db.session.flush()
            
            zamowienie.pozycje.append(pozycja)
        
        zamowienie.oblicz_wartosc()
        db.session.commit()
        
        Log.dodaj_log(g.user.id, 'Zamówienie do dostawcy', 
                     f'Utworzono zamówienie: {zamowienie.numer}')
        
        flash(f'Zamówienie {zamowienie.numer} zostało utworzone.', 'success')
        return redirect(url_for('orders.supplier_order_detail', zamowienie_id=zamowienie.id))
    
    dostawcy = Dostawca.query.filter_by(aktywny=True).order_by(Dostawca.nazwa).all()
    produkty = Produkt.query.filter_by(aktywny=True).order_by(Produkt.nazwa).all()
    
    return render_template('orders/supplier_order_form.html', 
                         dostawcy=dostawcy,
                         produkty=produkty)

@bp.route('/supplier')
@login_required
def supplier_orders_list():
    """Lista zamówień do dostawców"""
    zamowienia = ZamowienieZakupu.query.order_by(
        ZamowienieZakupu.data_zamowienia.desc()
    ).all()
    
    return render_template('orders/supplier_orders_list.html', zamowienia=zamowienia)

@bp.route('/supplier/<int:zamowienie_id>')
@login_required
def supplier_order_detail(zamowienie_id):
    """Szczegóły zamówienia do dostawcy"""
    zamowienie = ZamowienieZakupu.query.get_or_404(zamowienie_id)
    return render_template('orders/supplier_order_detail.html', zamowienie=zamowienie)

@bp.route('/supplier/<int:zamowienie_id>/status', methods=['POST'])
@role_required('Kierownik', 'Magazynier', 'Administrator')
def supplier_order_status(zamowienie_id):
    """Zmiana statusu zamówienia do dostawcy"""
    zamowienie = ZamowienieZakupu.query.get_or_404(zamowienie_id)
    nowy_status = StatusZamowieniaZakupu[request.form.get('status')]
    
    zamowienie.zmien_status(nowy_status)
    db.session.commit()
    
    flash(f'Status zamówienia został zmieniony na: {nowy_status.value}', 'success')
    return redirect(url_for('orders.supplier_order_detail', zamowienie_id=zamowienie_id))