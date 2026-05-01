# RadioDesk

> Application desktop de gestion de planning pour une station radio.  
> Gère les émissions, podcasts, utilisateurs et statistiques depuis une interface Qt native, sans dépendance réseau.

## Fonctionnalités principales

- **Planning** en 3 vues : liste, semaine (grille horaire), mois (calendrier)
- **Podcasts** : upload, lecture audio native (Qt Multimedia), gestion des fichiers
- **Dashboard** : statistiques temps réel, graphique d'activité (PyQtGraph), prochaines émissions
- **Gestion des utilisateurs** : CRUD complet avec 3 rôles (admin, animateur, technicien)
- **Export PDF** du planning via ReportLab
- **64 tests automatisés** (unit, intégration, E2E)

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | Pattern MVC, couches applicatives, schéma de modules |
| [Installation](docs/INSTALLATION.md) | Python, virtualenv, dépendances, lancement |
| [Base de données](docs/DATABASE.md) | Schéma SQLite, modèles ORM, migrations Alembic |
| [Fonctionnalités](docs/FEATURES.md) | Détail de chaque page et des rôles |
| [Tests](docs/TESTING.md) | Suite de tests, exécution, couverture |
| [Déploiement](docs/DEPLOYMENT.md) | Build PyInstaller, exécutable Windows, packaging |

## Démarrage rapide

```bash
# 1. Créer et activer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer l'application
python main.py
```

Compte administrateur par défaut créé au premier lancement :
- **Login** : `admin`
- **Mot de passe** : `admin`

## Stack technique

| Couche | Technologie |
|--------|-------------|
| **GUI** | PySide6 (Qt 6.6+) |
| **ORM** | SQLAlchemy 2.0 + SQLite |
| **Auth** | bcrypt 4.1 (hashage local) |
| **Export PDF** | ReportLab 4.0 |
| **Graphiques** | PyQtGraph 0.13 |
| **Tests** | pytest 7.4 + pytest-qt + pytest-cov |
| **Qualité** | flake8, black, mypy, pylint, pre-commit |
| **Packaging** | PyInstaller + Inno Setup (Windows) |

## Structure du projet

```
radiodesk/
├── main.py                     # Point d'entrée : QApplication + LoginWindow
├── requirements.txt            # Dépendances Python
├── pyproject.toml              # Config black, mypy, pytest, pylint
├── .pre-commit-config.yaml     # Hooks git : black, flake8
├── build.bat                   # Script de build Windows
├── src/
│   ├── config/settings.py      # Chemins DB, media, timeouts, logs
│   ├── db/database.py          # Initialisation SQLite + seed admin
│   ├── models/                 # ORM : User, Emission, Podcast, AuditLog
│   ├── auth/auth_service.py    # Login, session, require_role
│   ├── controllers/            # CRUD métier : emissions, users, podcasts
│   └── views/
│       ├── windows/            # Fenêtres Qt : login, main, dashboard, planning…
│       ├── dialogs/            # Modales (création/édition d'émission)
│       └── styles.py           # Feuille de style QSS globale
└── tests/
    ├── conftest.py             # Fixtures : DB in-memory, utilisateurs, sessions
    ├── unit/                   # 26 tests unitaires (auth, emissions, users)
    ├── integration/            # 6 tests d'intégration multi-couches
    └── e2e/                    # 32 tests E2E (UI Qt, vues calendrier)
```

## Rôles et permissions

| Rôle | Permissions |
|------|-------------|
| **admin** | CRUD utilisateurs, toutes émissions, toute configuration |
| **animateur** | CRUD ses propres émissions et podcasts |
| **technicien** | Lecture planning, modification du statut technique des émissions |

## Lancer les tests

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```
