# Assistant Enseignant (Django REST + React)

## Backend
    cd backend && python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python manage.py makemigrations core && python manage.py migrate
    python manage.py createsuperuser        # crée un compte enseignant (aussi via /admin/)
    python manage.py runserver

## Frontend
    cd frontend && npm install && npm run dev      # VITE_API_URL=http://localhost:8000/api par défaut

Aucun programme, canevas, règle de calcul ni modèle de bulletin officiel n'est codé en dur :
tout est configurable dans **Paramètres** (valeurs provisoires « à valider »).
