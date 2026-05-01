# Architecture — RadioDesk

## Vue d'ensemble

RadioDesk suit un pattern **MVC strict** avec une couche de service d'authentification transversale. Les couches sont découplées : les contrôleurs ignorent Qt, les vues ignorent SQLAlchemy. Ce découplage permet de tester la logique métier sans démarrer l'interface graphique.

```
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE VUE (Qt/PySide6)                  │
│                                                             │
│  LoginWindow     MainWindow (QStackedWidget)                │
│      │          ┌────────┬───────────┬──────────┐           │
│      │          │        │           │          │           │
│  DashboardPage  PlanningPage  PodcastsPage  UsersPage  …    │
│                                                             │
│  Les vues émettent des signaux Qt → appellent les controllers│
└───────────────────────────┬─────────────────────────────────┘
                            │  appels Python directs
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                COUCHE CONTRÔLEUR (Python pur)               │
│                                                             │
│  EmissionController    UserController    PodcastController  │
│      └─────────────────────┬──────────────────┘            │
│                            │  require_role()                │
│                    AuthService (session)                    │
└───────────────────────────┬─────────────────────────────────┘
                            │  SQLAlchemy ORM
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  COUCHE MODÈLE (SQLAlchemy)                  │
│                                                             │
│   User     Emission     Podcast     AuditLog                │
│      └──────────┴──────────┴──────────┘                     │
│                 SQLite (fichier local)                       │
└─────────────────────────────────────────────────────────────┘
```

## Détail des couches

### Couche Modèle (`src/models/`)

Classes SQLAlchemy héritant de `Base` (`src/models/base.py`). Elles définissent le schéma de la base et les relations ORM. **Aucune logique métier ici.**

| Modèle | Fichier | Responsabilité |
|--------|---------|---------------|
| `User` | `user.py` | Compte utilisateur, rôle, hash bcrypt |
| `Emission` | `emission.py` | Émission radio avec plage horaire |
| `Podcast` | `podcast.py` | Fichier audio lié à une émission |
| `AuditLog` | `audit_log.py` | Trace de toutes les actions |

### Couche Contrôleur (`src/controllers/`)

Contient toute la logique métier. Les contrôleurs reçoivent une `session` SQLAlchemy et le `current_user` de la part de la couche auth. **Aucun import Qt.**

```python
class EmissionController:
    def __init__(self, db_session: Session, auth_service: AuthService): ...

    def create(self, title, start_dt, end_dt, **kwargs) -> Emission:
        # Vérifie rôle, valide les dates, crée en base
        ...

    def get_week(self, date: datetime) -> list[Emission]:
        # Retourne les émissions de la semaine
        ...
```

### Couche Auth (`src/auth/auth_service.py`)

Service transversal gérant la session utilisateur. Les contrôleurs appellent `require_role('admin')` pour lever une exception si le rôle est insuffisant.

```python
auth = AuthService(db)
auth.login('admin', 'motdepasse')     # Retourne User ou lève AuthError
auth.require_role('animateur')         # Lève PermissionError si non autorisé
auth.current_user                      # User connecté (None si déconnecté)
auth.logout()                          # Efface la session
```

### Couche Vue (`src/views/`)

Widgets Qt purs. Chaque page est un `QWidget` ou `QMainWindow` qui :
1. Instancie les contrôleurs via injection de dépendances (`__init__(self, controllers)`)
2. Connecte les signaux Qt aux méthodes de contrôleur
3. Met à jour l'affichage depuis les données retournées

```python
class PlanningPage(QWidget):
    def __init__(self, emission_ctrl: EmissionController):
        self._ctrl = emission_ctrl
        self._btn_add.clicked.connect(self._on_add_emission)

    def _on_add_emission(self):
        dialog = EmissionDialog(self)
        if dialog.exec():
            emission = self._ctrl.create(**dialog.values())
            self._refresh_view()
```

## Flux de démarrage

```
main.py
  │
  ├─ Settings()          # Charge DB_PATH, MEDIA_PATH depuis pyproject.toml
  ├─ Database.init()     # Crée les tables SQLite + seed admin si première fois
  ├─ LoginWindow()       # Affiche le formulaire de connexion
  │      │
  │      └─ auth.login() # Vérifie credentials (bcrypt)
  │              │
  │              └─ MainWindow() # Charge la fenêtre principale
  │                     │
  │                     ├─ QStackedWidget (pages)
  │                     ├─ Sidebar avec navigation
  │                     └─ Instancie les contrôleurs (partagés entre pages)
  │
  └─ QApplication.exec() # Boucle d'événements Qt
```

## Injection de dépendances

Les contrôleurs sont instanciés une seule fois dans `MainWindow` et passés à chaque page via le constructeur. Cela évite les singletons globaux et facilite les tests.

```python
class MainWindow(QMainWindow):
    def __init__(self, db: Database, auth: AuthService):
        self._emission_ctrl = EmissionController(db.session, auth)
        self._user_ctrl = UserController(db.session, auth)
        self._podcast_ctrl = PodcastController(db.session, auth)

        self._pages = {
            'planning': PlanningPage(self._emission_ctrl),
            'users': UsersPage(self._user_ctrl),
            'podcasts': PodcastsPage(self._podcast_ctrl),
        }
```

## Décisions architecturales

**SQLite local sans serveur**  
Adapté à un usage mono-poste ou réseau local. Pas de configuration serveur, backup = copie du fichier `.db`. Alembic gère les migrations si le schéma évolue.

**MVC strict sans framework additionnel**  
PySide6 impose déjà une architecture signaux/slots. Le MVC pur est préféré à des solutions comme MVC-Qt ou QML pour rester explicite et testable.

**Tests sans Qt dans les contrôleurs**  
Les contrôleurs n'importent pas PySide6. Pytest peut les tester avec une base SQLite en mémoire (`:memory:`) sans démarrer de QApplication.
