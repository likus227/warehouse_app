FROM python:3.11-slim

# Ustawienie zmiennych środowiskowych
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Tworzenie katalogu roboczego
WORKDIR /app

# Kopiowanie plików wymagań
COPY requirements.txt .

# Instalacja zależności
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Kopiowanie całej aplikacji
COPY . .

# Utworzenie katalogu dla bazy danych
RUN mkdir -p instance

# Inicjalizacja bazy danych
RUN python init_db.py

# Otworzenie portu
EXPOSE 5000

# Uruchomienie aplikacji
CMD ["python", "run.py"]

# Dla produkcji użyj gunicorn (opcjonalne - zakomentowane)
# RUN pip install gunicorn
# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:create_app()"]