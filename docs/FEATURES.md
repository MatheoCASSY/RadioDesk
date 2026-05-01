# Fonctionnalités — RadioDesk

## Rôles et permissions

| Rôle | Dashboard | Planning | Podcasts | Music | Playlists | Utilisateurs | API Config |
|------|:---------:|:--------:|:--------:|:-----:|:---------:|:------------:|:----------:|
| **admin** | ✓ | ✓ CRUD | ✓ CRUD | ✓ | ✓ | ✓ CRUD | ✓ |
| **animateur** | ✓ | ✓ (ses émissions) | ✓ (ses podcasts) | ✓ | ✓ | — | — |
| **technicien** | ✓ | ✓ lecture + statut | ✓ lecture | — | — | — | — |

---

## Page Login (`src/views/windows/login_window.py`)

Fenêtre de démarrage. Formulaire username + password avec validation bcrypt.

**Comportements :**
- Erreur de credentials → message d'erreur inline, champ password vidé
- Compte désactivé → message spécifique (`Compte désactivé. Contacter l'admin.`)
- Succès → ouverture de `MainWindow` avec injection du rôle courant
- Touche `Entrée` sur le champ password → validation automatique

---

## Dashboard (`src/views/windows/dashboard_page.py`)

Page d'accueil affichée après connexion.

### Widgets

| Widget | Description |
|--------|-------------|
| **Compteurs** | Émissions du jour, animateurs actifs ce mois, podcasts ce mois |
| **Graphique activité** | Histogramme PyQtGraph des émissions par jour (7 derniers jours) |
| **Prochaines émissions** | Liste des 5 prochaines émissions avec titre, heure, animateur |
| **Statut technique** | Résumé des émissions par statut (`normal`, `en_test`, `probleme`, `ok`) |

---

## Planning (`src/views/windows/planning_page.py`)

Gestion du planning en **3 vues** avec sélecteur en haut de page.

### Vue Liste

`QTableWidget` avec toutes les émissions triées par date.

| Colonne | Description |
|---------|-------------|
| Titre | Nom de l'émission |
| Début | Date et heure de début |
| Fin | Date et heure de fin |
| Animateur | Prénom/nom de l'animateur |
| Statut | Badge coloré (`normal` / `en_test` / `probleme` / `ok`) |
| Actions | Boutons Éditer / Supprimer (selon rôle) |

**Filtres** : par animateur, par statut technique, par plage de dates.

### Vue Semaine

Grille 7 colonnes (lundi → dimanche) × lignes horaires (6h–23h).

- Les émissions sont représentées par des cellules colorées (couleur configurable)
- Les émissions longues fusionnent les cellules verticalement (`setSpan`)
- Navigation par semaine (← →) avec indicateur "Semaine du …"
- Clic sur une cellule → dialog d'édition si droit suffisant

### Vue Mois

`QCalendarWidget` enrichi avec badges sur les jours ayant des émissions.

- Navigation par mois
- Clic sur un jour → liste des émissions de ce jour en panneau latéral
- Couleur du badge = couleur de la première émission du jour

### Création / Édition d'émission

`EmissionDialog` (`src/views/dialogs/emission_dialog.py`) — modale PySide6.

| Champ | Type | Validation |
|-------|------|------------|
| Titre | `QLineEdit` | Requis, ≥ 3 caractères |
| Description | `QTextEdit` | Optionnel |
| Date début | `QDateTimeEdit` | Requis |
| Date fin | `QDateTimeEdit` | Requis, > début |
| Couleur | `QColorDialog` | Sélecteur de couleur |
| Statut technique | `QComboBox` | `normal`, `en_test`, `probleme`, `ok` |

### Export PDF

Bouton "Exporter PDF" disponible dans les 3 vues.

- Génère un PDF ReportLab de la vue courante
- Vue Liste → tableau récapitulatif
- Vue Semaine → grille de la semaine sélectionnée
- Vue Mois → calendrier du mois
- Dialogue de sauvegarde natif (`QFileDialog`)

---

## Podcasts (`src/views/windows/podcasts_page.py`)

### Liste des podcasts

`QListWidget` avec le titre, la durée formatée et l'émission associée.

### Lecteur audio

| Contrôle | Description |
|----------|-------------|
| ▶ Lire | Lance la lecture via `QMediaPlayer` |
| ⏸ Pause | Met en pause |
| ⏹ Stop | Arrête et revient au début |
| 🔊 Volume | `QSlider` horizontal, 0–100% |
| Progression | `QSlider` avec position courante / durée totale |

### Gestion des fichiers

- **Upload** : `QFileDialog` → accepte MP3, WAV, OGG, FLAC → copie dans `MEDIA_PATH`
- **Lier à une émission** : menu déroulant des émissions existantes
- **Supprimer** : supprime l'entrée en base + le fichier physique (avec confirmation)

---

## Gestion des utilisateurs (`src/views/windows/users_page.py`)

**Accès** : admin uniquement

`QTableWidget` avec toutes les comptes.

| Colonne | Description |
|---------|-------------|
| Username | Identifiant de connexion |
| Email | Adresse email |
| Rôle | Badge coloré par rôle |
| Actif | Interrupteur (désactiver sans supprimer) |
| Actions | Éditer / Réinitialiser MDP / Supprimer |

**Création d'utilisateur :**
- Username unique vérifié avant insertion
- Mot de passe hashé bcrypt à la création
- Rôle assigné parmi `admin`, `animateur`, `technicien`

**Réinitialisation de mot de passe :**
- L'admin saisit un nouveau mot de passe pour un utilisateur
- Confirmation requise (double saisie)
- Hashé et mis à jour en base

---

## Music Manager (`src/views/windows/music_manager_page.py`)

**Accès** : admin et animateur

Interface avancée de gestion de la bibliothèque musicale. Gère les fichiers audio en dehors du contexte émission/podcast.

---

## Playlists (`src/views/windows/playlist_manager_page.py`)

Interface de création et gestion des playlists. Permet de grouper des podcasts ou fichiers audio en séquences ordonnées.

---

## Configuration API (`src/views/windows/api_config_page.py`)

**Accès** : admin uniquement

Paramètres de connexion à une API externe (serveur Icecast/Liquidsoap ou API FluffRadio). Sauvegardés dans la configuration locale.

---

## Audit Log

Toutes les actions significatives sont tracées en base de données (`audit_logs`) :

| Action | Déclencheur |
|--------|-------------|
| `login` | Connexion réussie |
| `logout` | Déconnexion |
| `create_emission` | Nouvelle émission créée |
| `update_emission` | Émission modifiée |
| `delete_emission` | Émission supprimée |
| `create_user` | Nouvel utilisateur créé |
| `update_user` | Utilisateur modifié |
| `delete_user` | Utilisateur supprimé |
| `upload_podcast` | Podcast uploadé |
| `delete_podcast` | Podcast supprimé |
