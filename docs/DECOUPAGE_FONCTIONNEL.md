# Découpage fonctionnel — RadioDesk

RadioDesk suit un pattern **MVC (Modèle-Vue-Contrôleur)**. Chaque fonctionnalité implique trois couches :

- **Vue (Front)** — Les widgets PySide6/Qt qui affichent l'information et captent les interactions de l'utilisateur.
- **Contrôleur (Logique métier)** — Le code Python pur qui valide les données, applique les règles métier, vérifie les autorisations et orchestre les opérations.
- **Base de données (SQLite via SQLAlchemy)** — Le stockage persistant qui conserve, lit et modifie les données.

---

## 1. Authentification

**Objectif :** Permettre à un utilisateur de se connecter avec ses identifiants et d'obtenir un accès adapté à son rôle.

| Couche | Rôle |
|--------|------|
| **Vue** (`LoginWindow`) | Affiche le formulaire (username + password). Gère les événements clavier (touche Entrée). Affiche les messages d'erreur inline en cas d'échec. Redirige vers `MainWindow` en cas de succès. |
| **Contrôleur** (`AuthService.login()`) | Récupère l'utilisateur en base par son username. Compare le mot de passe saisi avec le hash bcrypt stocké. Lève une `AuthError` si les credentials sont invalides ou si le compte est désactivé. Stocke l'utilisateur connecté en session. |
| **BDD** (table `users`) | Fournit le hash bcrypt et le statut `active` du compte. Le rôle (`admin`, `animateur`, `technicien`) est chargé ici et transmis à toute l'application pour le contrôle d'accès. |

---

## 2. Dashboard

**Objectif :** Donner une vue synthétique de l'activité de la radio au moment de la connexion.

| Couche | Rôle |
|--------|------|
| **Vue** (`DashboardPage`) | Affiche les compteurs (émissions du jour, animateurs actifs, podcasts ce mois). Rend le graphique d'activité (histogramme PyQtGraph). Liste les 5 prochaines émissions et le résumé des statuts techniques. |
| **Contrôleur** (`EmissionController`, `PodcastController`) | Exécute les requêtes d'agrégation : compte les émissions du jour, filtre les prochaines émissions, regroupe par statut technique, calcule l'activité sur 7 jours. |
| **BDD** (tables `emissions`, `podcasts`, `users`) | Source de toutes les données agrégées. Les requêtes SQLAlchemy filtrent par plage de dates, comptent les enregistrements et joignent les tables pour obtenir les noms des animateurs. |

---

## 3. Planning des émissions

**Objectif :** Visualiser, créer, modifier et supprimer les émissions radio selon des vues hebdomadaire, mensuelle ou en liste.

| Couche | Rôle |
|--------|------|
| **Vue** (`PlanningPage`, `EmissionDialog`) | Propose trois vues sélectionnables (liste, semaine, mois). La vue liste affiche un `QTableWidget` avec filtres. La vue semaine dessine une grille horaire avec `setSpan`. La vue mois utilise un `QCalendarWidget` avec badges. `EmissionDialog` gère le formulaire de création/édition avec validation des champs. |
| **Contrôleur** (`EmissionController`) | Vérifie que l'utilisateur a le rôle requis (`require_role`). Valide les dates (fin > début). Crée, modifie ou supprime l'émission en base. Retourne les émissions filtrées par semaine, mois ou statut. Génère les données pour l'export PDF (ReportLab). |
| **BDD** (table `emissions`) | Stocke chaque émission avec ses dates, sa couleur, son statut technique et l'animateur responsable (`user_id` FK). Les requêtes filtrent par plage de dates pour alimenter chacune des trois vues. |

---

## 4. Gestion des podcasts

**Objectif :** Importer, écouter et organiser les fichiers audio des émissions.

| Couche | Rôle |
|--------|------|
| **Vue** (`PodcastsPage`) | Affiche la liste des podcasts via `QListWidget`. Propose les contrôles de lecture (▶ ⏸ ⏹), un slider de volume et une barre de progression via `QMediaPlayer`. Ouvre `QFileDialog` pour l'import de fichiers. Permet de lier un podcast à une émission via un menu déroulant. |
| **Contrôleur** (`PodcastController`) | Valide le format du fichier (MP3, WAV, OGG, FLAC). Calcule la durée audio à l'import. Copie le fichier dans `MEDIA_PATH`. Vérifie les droits avant suppression. Supprime l'entrée en base et le fichier physique. |
| **BDD** (table `podcasts`) | Stocke le titre, la description, le chemin du fichier, la durée et l'émission associée (`emission_id` FK). La relation avec `emissions` permet de retrouver tous les podcasts d'une émission. |

---

## 5. Gestion des utilisateurs

**Objectif :** Créer, modifier, désactiver et supprimer les comptes utilisateurs (admin uniquement).

| Couche | Rôle |
|--------|------|
| **Vue** (`UsersPage`) | Affiche un `QTableWidget` avec tous les comptes. Propose des boutons d'action (éditer, réinitialiser MDP, supprimer). Affiche les rôles sous forme de badges colorés. Intègre un interrupteur pour activer/désactiver un compte sans le supprimer. |
| **Contrôleur** (`UserController`) | Vérifie que l'appelant est `admin` via `require_role`. Valide l'unicité du username avant insertion. Hache le mot de passe avec bcrypt à la création et à la réinitialisation. Applique la suppression avec confirmation. |
| **BDD** (table `users`) | Stocke tous les comptes avec leurs rôles et hash de mot de passe. La colonne `active` permet de désactiver un compte sans perte de données. Les suppressions en cascade dans `emissions` et `audit_logs` préservent la cohérence. |

---

## 6. Bibliothèque musicale (Music Manager)

**Objectif :** Gérer les fichiers audio indépendants des émissions (musiques de fond, jingles, etc.).

| Couche | Rôle |
|--------|------|
| **Vue** (`MusicManagerPage`) | Interface de navigation dans la bibliothèque audio. Permet la sélection, la lecture et la gestion des métadonnées (titre, artiste, genre…). |
| **Contrôleur** | Gère l'import de fichiers audio, l'extraction des métadonnées, la validation des formats et les opérations CRUD sur les entrées de la bibliothèque. |
| **BDD** | Stocke les références aux fichiers audio avec leurs métadonnées pour permettre la recherche, le filtrage et l'association à d'autres entités. |

---

## 7. Playlists

**Objectif :** Regrouper des fichiers audio ou podcasts en séquences ordonnées.

| Couche | Rôle |
|--------|------|
| **Vue** (`PlaylistManagerPage`) | Interface de création et d'édition de playlists. Permet de réordonner les pistes par glisser-déposer, de nommer la playlist et de la lier à des émissions. |
| **Contrôleur** | Valide la structure de la playlist (au moins une piste, pas de doublon si requis). Orchestre l'ordre des pistes et les opérations CRUD. |
| **BDD** | Persiste l'ordre des pistes et les associations entre playlists et fichiers audio, permettant de reconstituer fidèlement la séquence lors de la lecture. |

---

## 8. Configuration API

**Objectif :** Permettre à l'administrateur de connecter RadioDesk à un serveur de streaming externe (Icecast/Liquidsoap ou API FluffRadio).

| Couche | Rôle |
|--------|------|
| **Vue** (`ApiConfigPage`) | Formulaire de saisie des paramètres de connexion (URL, token, identifiants). Bouton de test de connexion avec retour visuel. Accessible uniquement aux admins. |
| **Contrôleur** | Valide le format des URLs et des credentials. Sauvegarde la configuration dans un fichier local (`pyproject.toml` / fichier de config). Teste la connectivité avec un appel HTTP. |
| **BDD / Config** | Les paramètres sont stockés en configuration locale (pas en base SQLite) pour éviter de compromettre des credentials si la base est partagée. |

---

## 9. Audit Log

**Objectif :** Tracer toutes les actions significatives pour assurer la traçabilité et la sécurité.

| Couche | Rôle |
|--------|------|
| **Vue** | L'audit log n'a pas de vue dédiée : il est alimenté de façon transparente à chaque action. Une page de consultation pourrait être ajoutée pour les admins. |
| **Contrôleur** | Chaque contrôleur écrit une entrée dans `audit_logs` après chaque opération réussie (connexion, création, modification, suppression). Le user_id courant est toujours inclus. |
| **BDD** (table `audit_logs`) | Conserve un historique immuable de toutes les actions avec l'auteur, le type d'action, le détail et l'horodatage. La clé étrangère `user_id` est `SET NULL` (et non `CASCADE`) pour conserver les logs même si l'utilisateur est supprimé. |

---

## Synthèse du cheminement des données

```
Utilisateur interagit avec la Vue (PySide6)
        │
        ▼
Contrôleur reçoit la requête
  ├─ Vérifie les autorisations (AuthService.require_role)
  ├─ Valide les données métier
  ├─ Exécute la requête SQLAlchemy
  └─ Écrit dans audit_logs
        │
        ▼
Base de données SQLite (radiodesk.db)
  ├─ Lit / écrit les données
  └─ Retourne les objets ORM au Contrôleur
        │
        ▼
Contrôleur retourne les données à la Vue
        │
        ▼
Vue met à jour l'affichage (widgets Qt)
```

Chaque fonctionnalité suit ce même chemin : la **Vue** ne connaît pas SQLAlchemy, le **Contrôleur** ne connaît pas Qt, et la **BDD** ne contient aucune logique métier. Ce découplage garantit que chaque couche peut évoluer ou être testée indépendamment.
