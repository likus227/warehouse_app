from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.models import db, Uzytkownik, Log
from functools import wraps

bp = Blueprint('auth', __name__, url_prefix='/auth')

def login_required(f):
    """Dekorator wymagający zalogowania"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Musisz być zalogowany, aby uzyskać dostęp do tej strony.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Dekorator wymagający określonej roli"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Musisz być zalogowany.', 'warning')
                return redirect(url_for('auth.login'))
            
            user = Uzytkownik.query.get(session['user_id'])
            if user.rola.value not in roles:
                flash('Nie masz uprawnień do tej funkcji.', 'danger')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# UC1: Logowanie do systemu
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        haslo = request.form.get('haslo')
        
        user = Uzytkownik.query.filter_by(login=login, aktywny=True).first()
        
        if user and user.sprawdz_haslo(haslo):
            session.clear()
            session['user_id'] = user.id
            session['user_login'] = user.login
            session['user_role'] = user.rola.value
            session.permanent = True
            
            # Logowanie akcji
            Log.dodaj_log(user.id, 'Logowanie', f'Użytkownik {user.login} zalogował się', 
                         request.remote_addr)
            
            flash(f'Witaj, {user.imie}!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Nieprawidłowy login lub hasło.', 'danger')
    
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    if 'user_id' in session:
        user_id = session['user_id']
        login = session.get('user_login', 'Nieznany')
        Log.dodaj_log(user_id, 'Wylogowanie', f'Użytkownik {login} wylogował się')
    
    session.clear()
    flash('Zostałeś wylogowany.', 'info')
    return redirect(url_for('auth.login'))

@bp.before_app_request
def load_logged_in_user():
    """Ładuje dane zalogowanego użytkownika"""
    user_id = session.get('user_id')
    
    if user_id is None:
        from flask import g
        g.user = None
    else:
        from flask import g
        g.user = Uzytkownik.query.get(user_id)