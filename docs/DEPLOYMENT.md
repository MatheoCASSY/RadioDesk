# Déploiement — RadioDesk

RadioDesk est distribué sous forme d'un **exécutable autonome** — aucune installation Python requise sur la machine cible. Le packaging est réalisé avec **PyInstaller**.

## Prérequis de build

| Outil | Description |
|-------|-------------|
| Python 3.11+ | Dans le venv du projet |
| PyInstaller | `pip install pyinstaller` |
| Inno Setup 6 | Windows uniquement — crée l'installateur `.exe` |

## Build Windows

### 1. Méthode rapide (script)

```bash
# Depuis la racine du projet, venv activé
build.bat
```

Le script `build.bat` exécute automatiquement :
1. Nettoyage des dossiers `build/` et `dist/`
2. Compilation PyInstaller
3. (Optionnel) Packaging Inno Setup

### 2. Méthode manuelle

```bash
# Activer le venv
.venv\Scripts\activate

# Build PyInstaller (exécutable unique)
pyinstaller ^
  --onefile ^
  --windowed ^
  --name RadioDesk ^
  --icon assets/icon.ico ^
  --add-data "assets;assets" ^
  main.py

# Résultat : dist/RadioDesk.exe
```

| Option PyInstaller | Description |
|--------------------|-------------|
| `--onefile` | Un seul fichier `.exe` autonome |
| `--windowed` | Pas de console noire (application GUI) |
| `--name RadioDesk` | Nom de l'exécutable final |
| `--icon` | Icône `.ico` de l'application |
| `--add-data` | Inclure les assets dans le bundle |

### 3. Créer l'installateur (Inno Setup)

Après le build PyInstaller, ouvrir `setup/radiodesk.iss` dans Inno Setup Compiler et cliquer **Build → Compile**.

L'installateur `dist/RadioDesk-Setup.exe` :
- Installe dans `C:\Program Files\RadioDesk\`
- Crée un raccourci Bureau et dans le menu Démarrer
- Inclut un désinstallateur
- Détecte et installe les Visual C++ Redistributables si nécessaires

**Exemple de script Inno Setup (`setup/radiodesk.iss`) :**

```ini
[Setup]
AppName=RadioDesk
AppVersion=1.0.0
DefaultDirName={pf}\RadioDesk
DefaultGroupName=RadioDesk
OutputDir=..\dist
OutputBaseFilename=RadioDesk-Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "..\dist\RadioDesk.exe"; DestDir: "{app}"

[Icons]
Name: "{group}\RadioDesk"; Filename: "{app}\RadioDesk.exe"
Name: "{commondesktop}\RadioDesk"; Filename: "{app}\RadioDesk.exe"

[Run]
Filename: "{app}\RadioDesk.exe"; Description: "Lancer RadioDesk"; Flags: nowait postinstall skipifsilent
```

## Build macOS

```bash
# Sur macOS, dans le venv
pyinstaller \
  --onefile \
  --windowed \
  --name RadioDesk \
  --icon assets/icon.icns \
  --add-data "assets:assets" \
  main.py

# Résultat : dist/RadioDesk (ou dist/RadioDesk.app)
```

### Créer un `.dmg`

```bash
pip install dmgbuild
dmgbuild -s setup/dmgbuild_settings.py "RadioDesk" dist/RadioDesk.dmg
```

## Build Linux

```bash
pyinstaller \
  --onefile \
  --name radiodesk \
  --add-data "assets:assets" \
  main.py

# Résultat : dist/radiodesk (binaire standalone)
```

Distribuer via `.deb` ou `.AppImage` pour une meilleure intégration desktop.

## Données utilisateur

L'exécutable PyInstaller se décompresse dans un dossier temporaire. La base SQLite (`radiodesk.db`) et les médias (`media/`) sont créés dans le **répertoire courant** au premier lancement.

**Emplacement recommandé pour l'exécutable :**
```
C:\Program Files\RadioDesk\RadioDesk.exe   ← exécutable (lecture seule)
C:\Users\<user>\AppData\Roaming\RadioDesk\ ← données utilisateur (lecture/écriture)
```

Pour pointer les données vers `AppData`, modifier `src/config/settings.py` :

```python
import os
DATA_DIR = os.path.join(os.environ.get('APPDATA', '.'), 'RadioDesk')
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, 'radiodesk.db')
MEDIA_PATH = os.path.join(DATA_DIR, 'media')
```

## Versioning des releases

| Fichier | Où mettre la version |
|---------|---------------------|
| `pyproject.toml` | `[tool.poetry] version = "1.0.0"` |
| `setup/radiodesk.iss` | `AppVersion=1.0.0` |
| `src/config/settings.py` | `APP_VERSION = "1.0.0"` |

## Vérification post-build

Avant de distribuer l'exécutable :

```bash
# Tester sur une machine sans Python installé
dist\RadioDesk.exe

# Vérifier :
# - Fenêtre de login s'ouvre
# - Connexion admin/admin fonctionne
# - Création d'une émission fonctionne
# - Lecture audio fonctionne
```
