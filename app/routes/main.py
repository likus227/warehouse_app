from flask import Blueprint, render_template, redirect, url_for, flash, request, g, session
from app.models import db, Uzytkownik, RolaUzytkownika, Log, StanMagazynowy, Zamowienie
from app.routes.auth import login_required, role_required
from datetime import datetime, timedelta

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    """Panel główny - dostosowany do roli użytkownika"""
    from flask import session
    
    stats = {}
    
    if g.user.rola.value in ['Administrator', 'Kierownik']:
        # Statystyki dla administratora i kierownika
        stats['zamowienia_nowe'] = Zamowienie.query.filter_by(
            status='NOWE'
        ).count()
        
        stats['zamowienia_w_realizacji'] = Zamowienie.query.filter(
            Zamowienie.status.in_(['W_REALIZACJI', 'GOTOWE'])
        ).count()
        
        stats['produkty_niski_stan'] = StanMagazynowy.query.join(
            StanMagazynowy.produkt
        ).filter(
            StanMagazynowy.ilosc_dostepna <= db.bindparam('stan_min', 10)
        ).count()
        
        # Sprzedaż w tym miesiącu
        poczatek_miesiaca = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        stats['sprzedaz_miesiac'] = db.session.query(
            db.func.sum(Zamowienie.wartosc_brutto)
        ).filter(
            Zamowienie.data_zamowienia >= poczatek_miesiaca
        ).scalar() or 0
    
    return render_template('main/dashboard.html', stats=stats)

# UC2: Zarządzanie użytkownikami
@bp.route('/users')
@role_required('Administrator')
def users_list():
    """Lista użytkowników"""
    users = Uzytkownik.query.all()
    return render_template('main/users_list.html', users=users)

@bp.route('/users/add', methods=['GET', 'POST'])
@role_required('Administrator')
def user_add():
    """Dodawanie nowego użytkownika"""
    if request.method == 'POST':
        login = request.form.get('login')
        email = request.form.get('email')
        
        # Sprawdzenie czy użytkownik już istnieje
        if Uzytkownik.query.filter_by(login=login).first():
            flash('Użytkownik o tym loginie już istnieje.', 'danger')
            return render_template('main/user_form.html')
        
        if Uzytkownik.query.filter_by(email=email).first():
            flash('Użytkownik o tym adresie email już istnieje.', 'danger')
            return render_template('main/user_form.html')
        
        user = Uzytkownik(
            login=login,
            imie=request.form.get('imie'),
            nazwisko=request.form.get('nazwisko'),
            email=email,
            rola=RolaUzytkownika[request.form.get('rola')],
            aktywny=True
        )
        user.ustaw_haslo(request.form.get('haslo'))
        
        db.session.add(user)
        db.session.commit()
        
        Log.dodaj_log(g.user.id, 'Dodanie użytkownika', 
                     f'Dodano użytkownika: {user.login}')
        
        flash(f'Użytkownik {user.login} został dodany.', 'success')
        return redirect(url_for('main.users_list'))
    
    return render_template('main/user_form.html', roles=RolaUzytkownika)

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@role_required('Administrator')
def user_edit(user_id):
    """Edycja użytkownika"""
    user = Uzytkownik.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.imie = request.form.get('imie')
        user.nazwisko = request.form.get('nazwisko')
        user.email = request.form.get('email')
        user.rola = RolaUzytkownika[request.form.get('rola')]
        user.aktywny = request.form.get('aktywny') == 'on'
        
        # Zmiana hasła jeśli podano nowe
        nowe_haslo = request.form.get('nowe_haslo')
        if nowe_haslo:
            user.ustaw_haslo(nowe_haslo)
        
        db.session.commit()
        
        Log.dodaj_log(g.user.id, 'Edycja użytkownika', 
                     f'Edytowano użytkownika: {user.login}')
        
        flash(f'Dane użytkownika {user.login} zostały zaktualizowane.', 'success')
        return redirect(url_for('main.users_list'))
    
    return render_template('main/user_form.html', user=user, roles=RolaUzytkownika)

@bp.route('/users/<int:user_id>/toggle')
@role_required('Administrator')
def user_toggle(user_id):
    """Aktywacja/deaktywacja użytkownika"""
    user = Uzytkownik.query.get_or_404(user_id)
    
    if user.id == g.user.id:
        flash('Nie możesz dezaktywować własnego konta.', 'warning')
    else:
        user.aktywny = not user.aktywny
        db.session.commit()
        
        status = 'aktywowano' if user.aktywny else 'dezaktywowano'
        Log.dodaj_log(g.user.id, f'Zmiana statusu użytkownika', 
                     f'{status.capitalize()} użytkownika: {user.login}')
        
        flash(f'Użytkownik {user.login} został {status}.', 'success')
    
    return redirect(url_for('main.users_list'))

@bp.route('/profile')
@login_required
def profile():
    """Profil użytkownika"""
    return render_template('main/profile.html')

@bp.route('/profile/edit', methods=['POST'])
@login_required
def profile_edit():
    """Edycja własnego profilu"""
    g.user.imie = request.form.get('imie')
    g.user.nazwisko = request.form.get('nazwisko')
    g.user.email = request.form.get('email')
    
    # Zmiana hasła
    stare_haslo = request.form.get('stare_haslo')
    nowe_haslo = request.form.get('nowe_haslo')
    
    if stare_haslo and nowe_haslo:
        if g.user.sprawdz_haslo(stare_haslo):
            g.user.ustaw_haslo(nowe_haslo)
            flash('Hasło zostało zmienione.', 'success')
        else:
            flash('Nieprawidłowe stare hasło.', 'danger')
            return redirect(url_for('main.profile'))
    
    db.session.commit()
    flash('Profil został zaktualizowany.', 'success')
    return redirect(url_for('main.profile'))