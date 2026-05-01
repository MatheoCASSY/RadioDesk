# Tests — RadioDesk

RadioDesk dispose de **64 tests automatisés** couvrant les couches unit, intégration et E2E. Tous les tests tournent sur une base SQLite en mémoire (`:memory:`), sans état persistant entre les suites.

## Structure des tests

```
tests/
├── conftest.py                     # Fixtures partagées (DB, utilisateurs, sessions)
├── unit/
│   ├── test_auth_service.py        # 9 tests — login, roles, sessions
│   ├── test_emission_controller.py # 10 tests — CRUD, contrôle d'accès
│   └── test_user_controller.py     # 7 tests — CRUD, doublons
├── integration/
│   └── test_integration.py         # 6 tests — scénarios multi-couches
└── e2e/
    ├── test_ui_e2e.py              # 10 tests — interactions UI Qt
    └── test_planning_e2e.py        # 22 tests — logique des vues calendrier
```

## Lancer les tests

### Tous les tests

```bash
pytest tests/ -v
```

### Avec couverture de code

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

### Générer un rapport HTML de couverture

```bash
pytest tests/ --cov=src --cov-report=html
# Ouvrir htmlcov/index.html
```

### Filtrer par catégorie

```bash
# Tests unitaires uniquement
pytest tests/unit/ -v

# Tests E2E uniquement
pytest tests/e2e/ -v

# Tests d'un fichier spécifique
pytest tests/unit/test_auth_service.py -v

# Un test précis
pytest tests/unit/test_emission_controller.py::test_create_emission -v
```

### Tests Qt (mode headless)

Sur un serveur sans affichage (CI), ajouter la variable d'environnement :

```bash
QT_QPA_PLATFORM=offscreen pytest tests/ -v
```

## Fixtures (`tests/conftest.py`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `db` | `function` | Base SQLite en mémoire, tables créées, admin seedé |
| `session` | `function` | Session SQLAlchemy sur `db` |
| `admin_user` | `function` | Utilisateur `admin` connecté via `AuthService` |
| `animateur_user` | `function` | Utilisateur `animateur` sans droits admin |
| `technicien_user` | `function` | Utilisateur `technicien` en lecture seule |
| `auth_admin` | `function` | `AuthService` avec session admin active |
| `auth_animateur` | `function` | `AuthService` avec session animateur active |
| `emission_ctrl` | `function` | `EmissionController` injecté avec `auth_admin` |

**Exemple de fixture :**

```python
@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    database = Database.__new__(Database)
    database.engine = engine
    database._seed_admin()
    yield database
    Base.metadata.drop_all(engine)
```

## Tests unitaires

### `test_auth_service.py` (9 tests)

| Test | Vérifie |
|------|---------|
| `test_login_success` | Login avec credentials valides retourne l'utilisateur |
| `test_login_wrong_password` | Login avec mauvais MDP lève `AuthError` |
| `test_login_unknown_user` | Login utilisateur inexistant lève `AuthError` |
| `test_login_inactive_account` | Compte `active=False` lève `AuthError` |
| `test_require_role_admin_ok` | Admin peut appeler `require_role('admin')` sans exception |
| `test_require_role_insufficient` | Animateur sur `require_role('admin')` lève `PermissionError` |
| `test_session_expiry` | Session expirée (timeout) lève `AuthError` au prochain appel |
| `test_logout_clears_session` | `logout()` → `current_user` est `None` |
| `test_concurrent_login` | Deuxième login écrase la session précédente |

### `test_emission_controller.py` (10 tests)

| Test | Vérifie |
|------|---------|
| `test_create_emission` | Création avec données valides retourne une `Emission` avec ID |
| `test_create_emission_invalid_dates` | `end_dt <= start_dt` lève `ValueError` |
| `test_create_emission_animateur_own` | Animateur crée une émission avec son `user_id` |
| `test_create_emission_forbidden` | Technicien ne peut pas créer d'émission |
| `test_update_emission_admin` | Admin peut modifier n'importe quelle émission |
| `test_update_emission_own` | Animateur peut modifier ses propres émissions |
| `test_update_emission_other_forbidden` | Animateur ne peut pas modifier les émissions d'un autre |
| `test_delete_emission_cascade` | Suppression émission → podcasts liés supprimés |
| `test_get_week` | `get_week()` retourne uniquement les émissions de la semaine |
| `test_statut_technique_technicien` | Technicien peut changer `statut_technique` |

### `test_user_controller.py` (7 tests)

| Test | Vérifie |
|------|---------|
| `test_create_user` | Création d'un utilisateur avec hash bcrypt |
| `test_create_duplicate_username` | Username déjà pris lève `ValueError` |
| `test_create_duplicate_email` | Email déjà pris lève `ValueError` |
| `test_update_password` | Nouveau MDP correctement hashé |
| `test_deactivate_user` | `active=False` bloque le login |
| `test_delete_user_cascade` | Suppression utilisateur → ses émissions supprimées |
| `test_non_admin_cannot_manage_users` | Animateur ne peut pas appeler le `UserController` |

## Tests d'intégration

### `test_integration.py` (6 tests)

Scénarios qui traversent plusieurs couches (auth → controller → DB).

| Test | Scénario |
|------|---------|
| `test_full_emission_lifecycle` | Login admin → créer émission → modifier → supprimer → vérifier DB |
| `test_animateur_workflow` | Login animateur → créer émission → uploader podcast → vérifier lien |
| `test_role_escalation_blocked` | Animateur ne peut pas modifier le rôle d'un autre utilisateur |
| `test_session_timeout_workflow` | Session expirée → toute action de contrôleur lève `AuthError` |
| `test_podcast_cascade_delete` | Supprimer émission → podcast lié supprimé → fichier physique supprimé |
| `test_audit_log_created` | Toute action CRUD crée une entrée `audit_log` |

## Tests E2E

Les tests E2E utilisent **pytest-qt** pour interagir avec les widgets Qt.

### `test_ui_e2e.py` (10 tests)

Démarrage de `QApplication`, création de fenêtres et interactions simulées.

| Test | Scénario |
|------|---------|
| `test_login_window_shows` | La `LoginWindow` s'affiche sans erreur |
| `test_login_success_ui` | Saisie admin/admin → `MainWindow` s'ouvre |
| `test_login_failure_ui` | Mauvais MDP → message d'erreur visible dans l'UI |
| `test_main_window_navigation` | Clic sur chaque item de la sidebar → page correspondante affichée |
| `test_emission_dialog_validation` | Laisser le titre vide → bouton Valider désactivé |
| `test_emission_dialog_date_validation` | Fin < Début → erreur affichée |
| `test_create_emission_ui` | Remplir le dialog → clic Valider → émission apparaît dans la liste |
| `test_delete_emission_confirmation` | Clic Supprimer → dialog de confirmation → Oui → émission disparaît |
| `test_user_page_admin_only` | Technicien connecté → onglet Utilisateurs absent de la sidebar |
| `test_logout_returns_to_login` | Clic Déconnexion → `LoginWindow` réaffichée |

### `test_planning_e2e.py` (22 tests)

Logique des 3 vues de planning.

| Groupe | Nombre | Ce qui est testé |
|--------|--------|-----------------|
| Vue Liste | 6 | Tri, filtres, actions CRUD, export PDF |
| Vue Semaine | 8 | Navigation semaines, affichage cellules, fusion, clic |
| Vue Mois | 8 | Navigation mois, badges, sélection jour, liste latérale |

## CI (GitHub Actions)

```yaml
# .github/workflows/tests.yml (exemple)
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=src
        env:
          QT_QPA_PLATFORM: offscreen
```
