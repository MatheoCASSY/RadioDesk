# RadioDesk — Application Desktop de Gestion de Radio

> **Projet 2 — BTS SIO option SLAM — Épreuve E6 — 2025/2026**  
> Candidat : Mathéo Cassy · EPSI

Application client lourd Python/PySide6 (Qt 6) pour la gestion interne d'une radio : planning des émissions avec vues calendrier, gestion des utilisateurs et des rôles, podcasts avec lecture audio intégrée, tableau de bord avec graphiques. Fonctionne 100 % en local, sans aucune dépendance réseau, distribuable sous forme d'installeur.

---

## Stack technique

| Couche | Technologie | Rôle |
|---|---|---|
| Langage | Python 3.11+ | Langage unique, aucun JS/TS |
| Interface | PySide6 (Qt 6) | Fenêtres, widgets, signaux/slots |
| Base de données | SQLite via SQLAlchemy 2 | Persistance locale embarquée |
| Auth | bcrypt 12 rounds | Hashage des mots de passe |
| Audio | Qt Multimedia (QMediaPlayer) | Lecture intégrée des podcasts |
| Graphiques | PyQtGraph | Graphique d'activité hebdomadaire |
| PDF | reportlab | Export du planning en PDF |
| Tests | pytest + pytest-qt | Unitaires, intégration, E2E Qt |
| Linting | flake8 + pylint + black + mypy | Qualité et typage statique |
| Hooks | pre-commit | Vérification automatique avant commit |
| Packaging | PyInstaller + Inno Setup / dmgbuild | Installeur Windows/macOS/Linux |

> Architecture MVC stricte. Aucun service backend externe. Aucun JavaScript/TypeScript.

---

## Prérequis

- Python 3.11+
- pip
- (Windows) Microsoft Visual C++ Redistributable
- (Linux) `libxcb` et bibliothèques Qt système (`sudo apt install libxcb-cursor0`)

---

## Installation

### 1. Cloner et créer l'environnement virtuel

```bash
git clone <repo-url>
cd radiodesk
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Lancer l'application

```bash
python main.py
```

La base de données SQLite est créée automatiquement au premier lancement dans `~/.radiodesk/radiodesk.db`.

Un compte administrateur par défaut est créé :

| Nom d'utilisateur | Mot de passe | Rôle |
|---|---|---|
| admin | admin123456 | ADMIN |

**Changer ce mot de passe immédiatement après le premier login.**

---

## Variables de configuration

| Variable | Description | Défaut |
|---|---|---|
| `DB_PATH` | Chemin vers le fichier SQLite | `~/.radiodesk/radiodesk.db` |
| `MEDIA_PATH` | Dossier de stockage des podcasts | `~/.radiodesk/media/` |
| `SESSION_TIMEOUT` | Expiration de session (minutes) | `30` |
| `LOG_LEVEL` | Niveau de log (`DEBUG`/`INFO`) | `INFO` |

---

## Commandes

```bash
# Lancer l'application
python main.py

# Tests unitaires + intégration
pytest tests/unit tests/integration -v

# Tests E2E (interface Qt — nécessite un affichage ou DISPLAY=:0)
pytest tests/e2e -v

# Tous les tests avec rapport de couverture HTML
pytest --cov=src --cov-report=html

# Linting
flake8 src tests
pylint src

# Formatage automatique
black src tests

# Vérification des types
mypy src

# Initialiser les hooks pre-commit
pre-commit install
```

---

## Fonctionnalités

### Authentification et gestion des rôles

Écran de connexion au démarrage. Mots de passe hashés bcrypt (12 rounds). Session en mémoire avec expiration automatique (30 min d'inactivité).

| Rôle | Accès |
|---|---|
| **admin** | CRUD utilisateurs, toutes émissions, configuration |
| **animateur** | CRUD ses propres émissions, gestion de ses podcasts |
| **technicien** | Lecture planning, modification du statut technique des émissions |

### Planning des émissions — 3 vues

La page Planning propose trois modes d'affichage sélectionnables :

- **Vue Liste** — tableau complet de toutes les émissions avec actions (modifier, supprimer, changer le statut technique)
- **Vue Semaine** — grille horaire 7 jours (colonne par jour, ligne par heure de 6h à 23h), navigation semaine par semaine
- **Vue Mois** — calendrier mensuel (grille 7 × 6), navigation mois par mois, émissions affichées en pastilles colorées

Dans toutes les vues, un bouton **Exporter PDF** génère un fichier PDF du planning complet via reportlab.

### Gestion des podcasts

Ajout d'un fichier MP3/WAV associé à une émission. Lecture audio intégrée via Qt Multimedia (play/pause/stop, contrôle du volume). Fichiers stockés dans le dossier `MEDIA_PATH` configurable.

### Tableau de bord

Compteurs en temps réel (émissions du jour, animateurs actifs, podcasts ce mois). Liste des prochaines émissions (7 jours). Graphique à barres de l'activité hebdomadaire via PyQtGraph.

---

## Architecture

```
radiodesk/
├── main.py                         # Point d'entrée : QApplication + LoginWindow
├── requirements.txt
├── pyproject.toml                  # Config pytest, black, mypy, pylint
├── .pre-commit-config.yaml         # Hooks pre-commit (black, flake8)
├── src/
│   ├── config/
│   │   └── settings.py             # Paramètres (DB_PATH, MEDIA_PATH, timeouts)
│   ├── db/
│   │   └── database.py             # Moteur SQLAlchemy, init schéma, seed admin
│   ├── models/
│   │   ├── base.py                 # Base déclarative SQLAlchemy
│   │   ├── user.py                 # User (id, username, email, role, active)
│   │   ├── emission.py             # Emission (title, start_dt, end_dt, color, statut_technique)
│   │   ├── podcast.py              # Podcast (title, file_path, duration, emission_id)
│   │   └── audit_log.py            # AuditLog (action, timestamp, user_id)
│   ├── auth/
│   │   └── auth_service.py         # login, logout, session, require_role
│   ├── controllers/
│   │   ├── emission_controller.py  # CRUD émissions + contrôle d'accès par rôle
│   │   ├── user_controller.py      # CRUD utilisateurs (admin seulement)
│   │   └── podcast_controller.py   # Ajout/suppression + copie fichier audio
│   └── views/
│       ├── windows/
│       │   ├── login_window.py         # Écran de connexion
│       │   ├── main_window.py          # Fenêtre principale : sidebar + QStackedWidget
│       │   ├── dashboard_page.py       # Stats + graphique PyQtGraph + prochaines émissions
│       │   ├── planning_page.py        # Planning : vues Liste / Semaine / Mois + export PDF
│       │   ├── podcasts_page.py        # Liste podcasts + lecteur audio Qt Multimedia
│       │   ├── music_manager_page.py   # Gestionnaire audio avancé
│       │   └── users_page.py           # Admin : gestion des utilisateurs
│       └── dialogs/
│           └── emission_dialog.py      # Formulaire modal création/édition d'émission
└── tests/
    ├── conftest.py                 # Fixtures partagées (DB en mémoire, users, sessions)
    ├── unit/
    │   ├── test_auth_service.py          # Tests AuthService (login, rôles, session) — 9 tests
    │   ├── test_emission_controller.py   # Tests EmissionController (CRUD, droits) — 10 tests
    │   └── test_user_controller.py       # Tests UserController (CRUD, doublons) — 7 tests
    ├── integration/
    │   └── test_integration.py           # Scénarios complets multi-couches — 6 tests
    └── e2e/
        ├── test_ui_e2e.py                # Tests interface Qt (login, dialogs, accès) — 10 tests
        └── test_planning_e2e.py          # Tests vues calendrier planning — 22 tests
```

**Total : 64 tests automatisés, 0 échec.**

### Flux de données

```
QApplication
    │
    ▼
LoginWindow ──► AuthService.login(username, password)
                    │  bcrypt.checkpw(password, hash)
                    ▼
MainWindow (sidebar + QStackedWidget)
    ├── DashboardPage
    │       ├── EmissionController.list_all()
    │       └── PyQtGraph.PlotWidget (graphique activité)
    ├── PlanningPage  [Vue Liste | Vue Semaine | Vue Mois]
    │       ├── EmissionController.{list_all, create, update, delete}
    │       ├── AuthService.require_role(ADMIN | ANIMATEUR | TECHNICIEN)
    │       └── reportlab → export PDF
    ├── PodcastsPage
    │       ├── PodcastController.{list_for_emission, add, delete}
    │       └── QMediaPlayer (lecture audio intégrée)
    └── UsersPage (ADMIN seulement)
            └── UserController.{list_all, create, update_role, toggle_active, delete}
```

### Modèle de données (SQLite)

```
users
 ├── id              INTEGER PK
 ├── username        TEXT UNIQUE
 ├── email           TEXT UNIQUE
 ├── password_hash   TEXT
 ├── role            TEXT (admin | animateur | technicien)
 ├── active          BOOLEAN
 └── created_at      DATETIME

emissions
 ├── id              INTEGER PK
 ├── title           TEXT
 ├── description     TEXT
 ├── start_dt        DATETIME
 ├── end_dt          DATETIME
 ├── color           TEXT (#hex)
 ├── statut_technique TEXT (normal | en_test | probleme | ok)
 ├── user_id         FK → users.id (CASCADE DELETE)
 └── created_at      DATETIME

podcasts
 ├── id              INTEGER PK
 ├── title           TEXT
 ├── description     TEXT
 ├── file_path       TEXT (chemin local)
 ├── duration_seconds INTEGER
 ├── emission_id     FK → emissions.id (CASCADE DELETE)
 └── created_at      DATETIME

audit_logs
 ├── id        INTEGER PK
 ├── user_id   FK → users.id
 ├── action    TEXT
 ├── details   TEXT
 └── timestamp DATETIME
```

### Décisions techniques

**PySide6 vs Tkinter** — PySide6 (Qt 6) offre des widgets natifs de qualité professionnelle, un système de signaux/slots robuste, Qt Multimedia pour l'audio, et PyQtGraph pour les graphiques. Tkinter est insuffisant pour une application métier de cette ampleur.

**SQLAlchemy vs SQL brut** — SQLAlchemy fournit le mapping objet-relationnel, les migrations, et permet de tester avec une base en mémoire (`:memory:`) sans toucher au code de production.

**SQLite embarquée** — Zéro dépendance serveur. L'application tourne complètement en local. La migration vers PostgreSQL est possible en changeant uniquement `DATABASE_URL` dans `Settings`.

**Architecture MVC stricte** — Les controllers ne connaissent pas les vues. Les vues ne font jamais de requêtes directes à la base. Cette séparation rend les tests unitaires possibles sans instancier Qt.

**bcrypt (12 rounds)** — Hashage sécurisé avec salt aléatoire par utilisateur. Aucun mot de passe en clair.

**Vue Semaine/Mois** — Implémentées avec `QTableWidget` et `QStackedWidget`. La vue semaine utilise une grille heure × jour avec fusion de cellules (`setSpan`) pour les émissions longues. La vue mois utilise des `QWidget` personnalisés dans chaque cellule pour afficher les pastilles d'émissions.

---

## Qualité & Tests

### Stratégie de tests

| Type | Outil | Cible | Nombre |
|---|---|---|---|
| Tests unitaires | pytest + unittest.mock | Controllers, AuthService | 26 |
| Tests d'intégration | pytest + SQLite en mémoire | Scénarios CRUD complets | 6 |
| Tests E2E Qt | pytest-qt (QTest) | Fenêtres, dialogs, planning | 32 |
| **Total** | | | **64** |

### Scénarios E2E couverts

- Démarrage de l'application, écran de login, connexion réussie
- Connexion avec mauvais mot de passe (message d'erreur affiché)
- Création d'une émission depuis le tableau de bord
- Ajout d'un podcast à une émission
- Accès refusé à une section hors du rôle
- Technicien peut modifier le statut technique, ne peut pas créer ni supprimer
- Basculement entre les vues Liste, Semaine et Mois du planning
- Navigation temporelle (semaine suivante, mois précédent, retour à aujourd'hui)
- Présence des émissions dans la grille calendrier semaine
- Dimensions correctes des grilles (7 colonnes, 17 lignes horaires, 6 × 7 mois)

### Linting & Qualité

```bash
flake8 src tests       # Style PEP8
pylint src             # Analyse statique avancée
black src tests        # Formatage automatique
mypy src               # Vérification des types (type hints partout)
pre-commit run --all-files  # Tous les hooks
```

---

## Packaging — Créer un installeur

### Windows (`.exe` autonome + installeur)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name RadioDesk main.py
# Exécutable généré : dist/RadioDesk.exe
```

Pour créer un installeur `.exe` avec Inno Setup :
1. Télécharger [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Créer un script `.iss` pointant vers `dist/RadioDesk.exe`
3. Compiler → génère `RadioDesk-Setup.exe`

### macOS (`.dmg`)

```bash
pip install pyinstaller dmgbuild
pyinstaller --onefile --windowed --name RadioDesk main.py
dmgbuild -s setup/dmgbuild_settings.py "RadioDesk" dist/RadioDesk.dmg
```

### Linux (binaire autonome)

```bash
pip install pyinstaller
pyinstaller --onefile --name radiodesk main.py
# dist/radiodesk est un binaire autonome (pas de dépendance Python requise)
```

---

## CI/CD (GitHub Actions)

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Installer les dépendances
        run: |
          pip install -r requirements.txt
          sudo apt-get install -y libxcb-cursor0 libxcb1
      - name: Lint
        run: |
          flake8 src tests
          black src tests --check
      - name: Tests unitaires + intégration
        run: pytest tests/unit tests/integration -v --cov=src
        env:
          QT_QPA_PLATFORM: offscreen
      - name: Tests E2E Qt
        run: pytest tests/e2e -v
        env:
          QT_QPA_PLATFORM: offscreen

  build-windows:
    needs: test
    runs-on: windows-latest
    if: startsWith(github.ref, 'refs/tags/')
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt pyinstaller
      - run: pyinstaller --onefile --windowed --name RadioDesk main.py
      - uses: actions/upload-artifact@v4
        with:
          name: RadioDesk-Windows
          path: dist/RadioDesk.exe
```
