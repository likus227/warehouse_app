from flask import Blueprint, render_template, redirect, url_for, flash, request, g
from app.models import db, Klient, Log
from app.routes.auth import login_required, role_required

bp = Blueprint('customers', __name__, url_prefix='/customers')

# UC12: Zarządzanie klientami
@bp.route('/')
@login_required
def list():
    """Lista klientów"""
    page = request.args.get('page', 1, type=int)
    szukaj = request.args.get('szukaj', '')
    
    query = Klient.query
    
    if szukaj:
        query = query.filter(
            db.or_(
                Klient.nazwa.contains(szukaj),
                Klient.nip.contains(szukaj),
                Klient.email.contains(szukaj)
            )
        )
    
    klienci = query.order_by(Klient.nazwa).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('customers/list.html', klienci=klienci, szukaj=szukaj)

@bp.route('/add', methods=['GET', 'POST'])
@role_required('Sprzedawca', 'Administrator')
def add():
    """Dodawanie nowego klienta"""
    if request.method == 'POST':
        nip = request.form.get('nip')
        
        # Sprawdzenie czy klient już istnieje
        if nip and Klient.query.filter_by(nip=nip).first():
            flash('Klient o tym NIP już istnieje.', 'danger')
            return render_template('customers/form.html')
        
        klient = Klient(
            nazwa=request.form.get('nazwa'),
            nip=nip,
            adres=request.form.get('adres'),
            kod_pocztowy=request.form.get('kod_pocztowy'),
            miasto=request.form.get('miasto'),
            telefon=request.form.get('telefon'),
            email=request.form.get('email'),
            aktywny=True
        )
        
        db.session.add(klient)
        db.session.commit()
        
        Log.dodaj_log(g.user.id, 'Dodanie klienta', 
                     f'Dodano klienta: {klient.nazwa}')
        
        flash(f'Klient {klient.nazwa} został dodany.', 'success')
        return redirect(url_for('customers.detail', klient_id=klient.id))
    
    return render_template('customers/form.html')

@bp.route('/<int:klient_id>')
@login_required
def detail(klient_id):
    """Szczegóły klienta"""
    klient = Klient.query.get_or_404(klient_id)
    return render_template('customers/detail.html', klient=klient)

@bp.route('/<int:klient_id>/edit', methods=['GET', 'POST'])
@role_required('Sprzedawca', 'Administrator')
def edit(klient_id):
    """Edycja klienta"""
    klient = Klient.query.get_or_404(klient_id)
    
    if request.method == 'POST':
        klient.nazwa = request.form.get('nazwa')
        klient.nip = request.form.get('nip')
        klient.adres = request.form.get('adres')
        klient.kod_pocztowy = request.form.get('kod_pocztowy')
        klient.miasto = request.form.get('miasto')
        klient.telefon = request.form.get('telefon')
        klient.email = request.form.get('email')
        klient.aktywny = request.form.get('aktywny') == 'on'
        
        db.session.commit()
        
        Log.dodaj_log(g.user.id, 'Edycja klienta', 
                     f'Edytowano klienta: {klient.nazwa}')
        
        flash(f'Dane klienta {klient.nazwa} zostały zaktualizowane.', 'success')
        return redirect(url_for('customers.detail', klient_id=klient.id))
    
    return render_template('customers/form.html', klient=klient)

@bp.route('/<int:klient_id>/toggle')
@role_required('Sprzedawca', 'Administrator')
def toggle(klient_id):
    """Aktywacja/deaktywacja klienta"""
    klient = Klient.query.get_or_404(klient_id)
    klient.aktywny = not klient.aktywny
    db.session.commit()
    
    status = 'aktywowano' if klient.aktywny else 'dezaktywowano'
    Log.dodaj_log(g.user.id, f'Zmiana statusu klienta', 
                 f'{status.capitalize()} klienta: {klient.nazwa}')
    
    flash(f'Klient {klient.nazwa} został {status}.', 'success')
    return redirect(url_for('customers.list'))