from flask import Blueprint, render_template, redirect, url_for, flash, request, g
from app.models import db, Produkt, StanMagazynowy, Log
from app.routes.auth import login_required, role_required
from decimal import Decimal

bp = Blueprint('products', __name__, url_prefix='/products')

# UC3: Zarządzanie produktami
@bp.route('/')
@login_required
def list():
    """Lista produktów"""
    page = request.args.get('page', 1, type=int)
    kategoria = request.args.get('kategoria', '')
    szukaj = request.args.get('szukaj', '')
    
    query = Produkt.query
    
    if kategoria:
        query = query.filter_by(kategoria=kategoria)
    
    if szukaj:
        query = query.filter(
            db.or_(
                Produkt.kod.contains(szukaj),
                Produkt.nazwa.contains(szukaj)
            )
        )
    
    produkty = query.order_by(Produkt.nazwa).paginate(
        page=page, per_page=20, error_out=False
    )
    
    kategorie = db.session.query(Produkt.kategoria).distinct().all()
    kategorie = [k[0] for k in kategorie if k[0]]
    
    return render_template('products/list.html', 
                         produkty=produkty, 
                         kategorie=kategorie,
                         aktywna_kategoria=kategoria,
                         szukaj=szukaj)

@bp.route('/add', methods=['GET', 'POST'])
@role_required('Administrator')
def add():
    """Dodawanie nowego produktu"""
    if request.method == 'POST':
        kod = request.form.get('kod')
        
        # Sprawdzenie czy produkt już istnieje
        if Produkt.query.filter_by(kod=kod).first():
            flash('Produkt o tym kodzie już istnieje.', 'danger')
            return render_template('products/form.html')
        
        produkt = Produkt(
            kod=kod,
            nazwa=request.form.get('nazwa'),
            kategoria=request.form.get('kategoria'),
            jednostka=request.form.get('jednostka', 'szt'),
            cena_jednostkowa=Decimal(request.form.get('cena_jednostkowa')),
            stan_minimalny=int(request.form.get('stan_minimalny', 10)),
            opis=request.form.get('opis'),
            aktywny=True
        )
        
        db.session.add(produkt)
        db.session.flush()  # Aby uzyskać ID produktu
        
        # Utworzenie stanu magazynowego
        stan = StanMagazynowy(
            produkt_id=produkt.id,
            ilosc_dostepna=0,
            ilosc_zarezerwowana=0,
            lokalizacja=request.form.get('lokalizacja', '')
        )
        
        db.session.add(stan)
        db.session.commit()
        
        Log.dodaj_log(g.user.id, 'Dodanie produktu', 
                     f'Dodano produkt: {produkt.kod} - {produkt.nazwa}')
        
        flash(f'Produkt {produkt.nazwa} został dodany.', 'success')
        return redirect(url_for('products.list'))
    
    return render_template('products/form.html')

@bp.route('/<int:produkt_id>')
@login_required
def detail(produkt_id):
    """Szczegóły produktu"""
    produkt = Produkt.query.get_or_404(produkt_id)
    return render_template('products/detail.html', produkt=produkt)

@bp.route('/<int:produkt_id>/edit', methods=['GET', 'POST'])
@role_required('Administrator')
def edit(produkt_id):
    """Edycja produktu"""
    produkt = Produkt.query.get_or_404(produkt_id)
    
    if request.method == 'POST':
        produkt.nazwa = request.form.get('nazwa')
        produkt.kategoria = request.form.get('kategoria')
        produkt.jednostka = request.form.get('jednostka')
        produkt.cena_jednostkowa = Decimal(request.form.get('cena_jednostkowa'))
        produkt.stan_minimalny = int(request.form.get('stan_minimalny'))
        produkt.opis = request.form.get('opis')
        produkt.aktywny = request.form.get('aktywny') == 'on'
        
        if produkt.stan_magazynowy:
            produkt.stan_magazynowy.lokalizacja = request.form.get('lokalizacja')
        
        db.session.commit()
        
        Log.dodaj_log(g.user.id, 'Edycja produktu', 
                     f'Edytowano produkt: {produkt.kod} - {produkt.nazwa}')
        
        flash(f'Produkt {produkt.nazwa} został zaktualizowany.', 'success')
        return redirect(url_for('products.detail', produkt_id=produkt.id))
    
    return render_template('products/form.html', produkt=produkt)

@bp.route('/<int:produkt_id>/toggle')
@role_required('Administrator')
def toggle(produkt_id):
    """Aktywacja/deaktywacja produktu"""
    produkt = Produkt.query.get_or_404(produkt_id)
    produkt.aktywny = not produkt.aktywny
    db.session.commit()
    
    status = 'aktywowano' if produkt.aktywny else 'dezaktywowano'
    Log.dodaj_log(g.user.id, f'Zmiana statusu produktu', 
                 f'{status.capitalize()} produkt: {produkt.kod}')
    
    flash(f'Produkt {produkt.nazwa} został {status}.', 'success')
    return redirect(url_for('products.list'))