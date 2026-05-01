# Installation — RadioDesk

## Prérequis

| Outil | Version minimale | Notes |
|-------|-----------------|-------|
| Python | 3.11+ | 3.12 recommandé |
| pip | 23.x | Inclus avec Python |
| Git | 2.x | Pour les hooks pre-commit |

> **Windows** : Télécharger Python depuis [python.org](https://python.org). Cocher "Add Python to PATH" à l'installation.  
> **Linux** : `sudo apt install python3.12 python3.12-venv python3-pip`  
> **macOS** : `brew install python@3.12`

## 1. Cloner le dépôt

```bash
git clone <url-du-dépôt>
cd radiodesk
```

## 2. Créer l'environnement virtuel

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

Vérifier que l'environnement est actif (le prompt affiche `(.venv)`) :

```bash
python --version   # Doit afficher 3.11+ dans le venv
```

## 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### Dépendances principales

| Package | Version | Usage |
|---------|---------|-------|
| `PySide6` | ≥6.6.0 | Framework Qt 6 (GUI) |
| `SQLAlchemy` | ≥2.0.0 | ORM SQLite |
| `bcrypt` | ≥4.1.0 | Hashage des mots de passe |
| `reportlab` | ≥4.0.0 | Export PDF du planning |
| `pyqtgraph` | ≥0.13.0 | Graphique d'activité |
| `alembic` | ≥1.13.0 | Migrations de base de données |
| `requests` | ≥2.31.0 | Requêtes HTTP (intégration API) |

### Dépendances de développement

| Package | Usage |
|---------|-------|
| `pytest` + `pytest-qt` + `pytest-cov` | Tests automatisés |
| `flake8` + `pylint` + `black` | Linting + formatage |
| `mypy` | Vérification de types |
| `pre-commit` | Hooks git automatiques |

## 4. Installer les hooks pre-commit (développement)

```bash
pre-commit install
```

Les hooks vérifient automatiquement le formatage `black` et `flake8` avant chaque commit.

## 5. Lancer l'application

```bash
python main.py
```

Au premier lancement, RadioDesk :
1. Crée le fichier SQLite (`radiodesk.db` dans le répertoire courant)
2. Crée toutes les tables (ORM SQLAlchemy)
3. Insère un compte administrateur par défaut

**Credentials par défaut :**
- Login : `admin`
- Mot de passe : `admin`

> Changer le mot de passe admin dès le premier lancement dans la section **Utilisateurs**.

## 6. Configuration

Les paramètres sont dans `src/config/settings.py` :

| Paramètre | Valeur par défaut | Description |
|-----------|------------------|-------------|
| `DB_PATH` | `radiodesk.db` | Chemin du fichier SQLite |
| `MEDIA_PATH` | `media/` | Dossier de stockage des podcasts |
| `SESSION_TIMEOUT` | `3600` | Durée de session en secondes |
| `LOG_LEVEL` | `INFO` | Niveau de logs (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

## Dépannage

| Problème | Cause probable | Solution |
|----------|---------------|----------|
| `ModuleNotFoundError: PySide6` | Venv non activé ou install manqué | Activer le venv + `pip install -r requirements.txt` |
| Fenêtre ne s'ouvre pas | `QT_QPA_PLATFORM` non défini sur serveur sans display | `export QT_QPA_PLATFORM=offscreen` (pour les tests CI) |
| `OperationalError: no such table` | DB corrompue ou migrée partiellement | Supprimer `radiodesk.db` et relancer (⚠️ perte de données) |
| `bcrypt: Invalid salt` | Ancien hash en base incompatible | Réinitialiser le mot de passe en base via le shell Python |
| Podcast ne joue pas | Codec multimedia manquant | Installer `gstreamer` (Linux) ou vérifier Qt Multimedia |

### Réinitialiser la base de données

```bash
# ATTENTION : supprime toutes les données
python -c "
from src.db.database import Database
from src.config.settings import Settings
s = Settings()
import os; os.remove(s.db_path)
Database(s.db_path).init()
print('Base réinitialisée.')
"
```
