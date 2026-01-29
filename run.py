from app import create_app, db
from app.models import *
import os

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'Uzytkownik': Uzytkownik, 
        'Produkt': Produkt,
        'StanMagazynowy': StanMagazynowy,
        'Klient': Klient,
        'Dostawca': Dostawca,
        'Zamowienie': Zamowienie,
        'Faktura': Faktura
    }

if __name__ == '__main__':
    # Tryb produkcyjny lub deweloperski w zależności od zmiennej środowiskowej
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)