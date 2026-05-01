# Base de données — RadioDesk

RadioDesk utilise **SQLite** via **SQLAlchemy 2.0** (ORM déclaratif). La base est un fichier local (`radiodesk.db`). Les migrations sont gérées par **Alembic**.

## Schéma (diagramme ER)

```
┌─────────────────────────┐          ┌──────────────────────────────┐
│          users          │          │          emissions            │
├─────────────────────────┤          ├──────────────────────────────┤
│ id          INTEGER PK  │◄─────────│ user_id     INTEGER FK       │
│ username    TEXT UNIQUE │  1     N │ id          INTEGER PK       │
│ email       TEXT UNIQUE │          │ title       TEXT NOT NULL    │
│ password_hash TEXT      │          │ description TEXT             │
│ role        TEXT        │          │ start_dt    DATETIME         │
│ active      BOOLEAN     │          │ end_dt      DATETIME         │
│ created_at  DATETIME    │          │ color       TEXT             │
└─────────────────────────┘          │ statut_technique TEXT        │
           │                         │ created_at  DATETIME         │
           │ 1                       └──────────────┬───────────────┘
           │                                        │ 1
           │ N                                      │
┌──────────┴──────────────┐          ┌──────────────▼───────────────┐
│       audit_logs        │          │           podcasts            │
├─────────────────────────┤          ├──────────────────────────────┤
│ id          INTEGER PK  │          │ id          INTEGER PK       │
│ user_id     INTEGER FK  │          │ emission_id INTEGER FK       │
│ action      TEXT        │          │ title       TEXT NOT NULL    │
│ details     TEXT        │          │ description TEXT             │
│ timestamp   DATETIME    │          │ file_path   TEXT             │
└─────────────────────────┘          │ duration_seconds INTEGER     │
                                     │ created_at  DATETIME         │
                                     └──────────────────────────────┘
```

## Tables

### `users`

Représente les comptes utilisateurs de l'application.

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | INTEGER | PK, autoincrement | Identifiant unique |
| `username` | TEXT | NOT NULL, UNIQUE | Identifiant de connexion |
| `email` | TEXT | UNIQUE | Adresse email |
| `password_hash` | TEXT | NOT NULL | Hash bcrypt du mot de passe |
| `role` | TEXT | NOT NULL, DEFAULT `animateur` | `admin`, `animateur`, `technicien` |
| `active` | BOOLEAN | DEFAULT `True` | Compte activé/désactivé |
| `created_at` | DATETIME | DEFAULT now | Date de création |

**Rôles valides :** `admin` · `animateur` · `technicien`

---

### `emissions`

Représente une émission radio planifiée.

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | INTEGER | PK, autoincrement | Identifiant unique |
| `title` | TEXT | NOT NULL | Titre de l'émission |
| `description` | TEXT | — | Description optionnelle |
| `start_dt` | DATETIME | NOT NULL | Début de l'émission |
| `end_dt` | DATETIME | NOT NULL | Fin de l'émission |
| `color` | TEXT | DEFAULT `#4A90E2` | Couleur hex d'affichage dans le planning |
| `statut_technique` | TEXT | DEFAULT `normal` | État technique |
| `user_id` | INTEGER | FK → `users.id` CASCADE | Animateur responsable |
| `created_at` | DATETIME | DEFAULT now | Date de création |

**Statuts techniques :**
- `normal` — Emission standard
- `en_test` — En cours de test technique
- `probleme` — Problème technique signalé
- `ok` — Validé techniquement

---

### `podcasts`

Fichiers audio enregistrés, liés à une émission.

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | INTEGER | PK, autoincrement | Identifiant unique |
| `title` | TEXT | NOT NULL | Titre du podcast |
| `description` | TEXT | — | Description optionnelle |
| `file_path` | TEXT | NOT NULL | Chemin absolu vers le fichier audio |
| `duration_seconds` | INTEGER | — | Durée en secondes (calculée à l'import) |
| `emission_id` | INTEGER | FK → `emissions.id` CASCADE | Emission associée |
| `created_at` | DATETIME | DEFAULT now | Date d'ajout |

**Formats supportés :** MP3, WAV, OGG, FLAC

---

### `audit_logs`

Trace immuable de toutes les actions utilisateurs.

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | INTEGER | PK, autoincrement | Identifiant unique |
| `user_id` | INTEGER | FK → `users.id` SET NULL | Auteur de l'action |
| `action` | TEXT | NOT NULL | Nom de l'action (`create_emission`, `login`, `delete_user`…) |
| `details` | TEXT | — | JSON ou texte libre avec le contexte |
| `timestamp` | DATETIME | DEFAULT now | Horodatage |

---

## Modèles SQLAlchemy

### Exemple : `Emission`

```python
class Emission(Base):
    __tablename__ = 'emissions'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    start_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    color: Mapped[str] = mapped_column(Text, default='#4A90E2')
    statut_technique: Mapped[str] = mapped_column(Text, default='normal')
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))

    user: Mapped['User'] = relationship(back_populates='emissions')
    podcasts: Mapped[list['Podcast']] = relationship(
        back_populates='emission', cascade='all, delete-orphan'
    )
```

## Initialisation (`src/db/database.py`)

```python
class Database:
    def __init__(self, db_path: str):
        self.engine = create_engine(f'sqlite:///{db_path}')

    def init(self):
        Base.metadata.create_all(self.engine)
        self._seed_admin()

    def _seed_admin(self):
        # Crée l'admin par défaut uniquement si aucun utilisateur n'existe
        with Session(self.engine) as session:
            if not session.query(User).first():
                admin = User(
                    username='admin',
                    email='admin@radiodesk.local',
                    password_hash=bcrypt.hashpw(b'admin', bcrypt.gensalt()),
                    role='admin',
                )
                session.add(admin)
                session.commit()
```

## Migrations Alembic

### Initialiser Alembic (fait une seule fois)

```bash
alembic init alembic
# Modifier alembic.ini : sqlalchemy.url = sqlite:///radiodesk.db
```

### Créer une migration

```bash
alembic revision --autogenerate -m "add_column_to_emissions"
```

### Appliquer les migrations

```bash
alembic upgrade head
```

### Revenir en arrière

```bash
alembic downgrade -1
```

## Backup

La base de données est un fichier SQLite unique. Backup = copie du fichier.

```bash
# Backup manuel
cp radiodesk.db radiodesk.backup.$(date +%Y%m%d).db

# Restauration
cp radiodesk.backup.20250115.db radiodesk.db
```
