from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox, QFrame, QSplitter,
    QInputDialog, QProgressBar
)
from PySide6.QtCore import Qt, QThreadPool
from src.lib.api_client import ApiConfigManager
from src.lib.worker import ApiWorker


class PlaylistManagerPage(QWidget):
    def __init__(self, config_manager: ApiConfigManager) -> None:
        super().__init__()
        self._cfg = config_manager
        self._playlists: list[dict] = []
        self._selected: dict | None = None
        self._tracks: list[dict] = []
        self._all_musics: list[dict] = []
        self._pool = QThreadPool.globalInstance()
        self._setup_ui()
        self._load_all()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 20)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Gestion des playlists")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()
        self._save_btn = QPushButton("💾  Sauvegarder")
        self._save_btn.setObjectName("primaryBtn")
        self._save_btn.setFixedHeight(36)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_playlist)
        header.addWidget(self._save_btn)
        layout.addLayout(header)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #6b7280; font-size: 12px; background: transparent; border: none;")
        layout.addWidget(self._status)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedHeight(4)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: playlist list
        left = QFrame()
        left.setObjectName("statCard")
        left.setFixedWidth(220)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(12, 12, 12, 12)
        ll.setSpacing(8)
        pl_header = QHBoxLayout()
        pl_lbl = QLabel("Playlists")
        pl_lbl.setStyleSheet("font-weight: 700; font-size: 13px; background: transparent; border: none;")
        pl_header.addWidget(pl_lbl)
        pl_header.addStretch()
        new_btn = QPushButton("+")
        new_btn.setObjectName("primaryBtn")
        new_btn.setFixedSize(28, 28)
        new_btn.clicked.connect(self._create_playlist)
        pl_header.addWidget(new_btn)
        ll.addLayout(pl_header)
        self._pl_list = QListWidget()
        self._pl_list.currentItemChanged.connect(self._on_playlist_selected)
        ll.addWidget(self._pl_list, 1)
        del_pl_btn = QPushButton("🗑  Supprimer")
        del_pl_btn.setObjectName("dangerBtn")
        del_pl_btn.clicked.connect(self._delete_playlist)
        ll.addWidget(del_pl_btn)
        splitter.addWidget(left)

        # Right: music browser + playlist tracks
        right = QFrame()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)

        inner_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Available musics
        avail = QFrame()
        avail.setObjectName("statCard")
        al = QVBoxLayout(avail)
        al.setContentsMargins(12, 12, 12, 12)
        al.setSpacing(8)
        al_lbl = QLabel("Musiques disponibles")
        al_lbl.setStyleSheet("font-weight: 700; font-size: 13px; background: transparent; border: none;")
        self._music_search = QLineEdit()
        self._music_search.setPlaceholderText("🔍  Rechercher…")
        self._music_search.setFixedHeight(34)
        self._music_search.textChanged.connect(self._filter_musics)
        al.addWidget(al_lbl)
        al.addWidget(self._music_search)
        self._music_table = QTableWidget(0, 3)
        self._music_table.setHorizontalHeaderLabels(["Titre", "Artiste", ""])
        self._music_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._music_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._music_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._music_table.setColumnWidth(2, 40)
        self._music_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._music_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        al.addWidget(self._music_table, 1)
        add_sel_btn = QPushButton("➕  Ajouter la sélection")
        add_sel_btn.setObjectName("editBtn")
        add_sel_btn.clicked.connect(self._add_selected_to_playlist)
        al.addWidget(add_sel_btn)
        inner_splitter.addWidget(avail)

        # Playlist tracks
        tracks_frame = QFrame()
        tracks_frame.setObjectName("statCard")
        tl = QVBoxLayout(tracks_frame)
        tl.setContentsMargins(12, 12, 12, 12)
        tl.setSpacing(8)
        self._tracks_lbl = QLabel("Pistes de la playlist")
        self._tracks_lbl.setStyleSheet("font-weight: 700; font-size: 13px; background: transparent; border: none;")
        tl.addWidget(self._tracks_lbl)
        self._tracks_table = QTableWidget(0, 3)
        self._tracks_table.setHorizontalHeaderLabels(["#", "Titre", ""])
        self._tracks_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._tracks_table.setColumnWidth(0, 40)
        self._tracks_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._tracks_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._tracks_table.setColumnWidth(2, 40)
        self._tracks_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tracks_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tl.addWidget(self._tracks_table, 1)

        # Up/Down move buttons
        move_row = QHBoxLayout()
        up_btn = QPushButton("▲  Monter")
        up_btn.setObjectName("editBtn")
        up_btn.clicked.connect(self._move_up)
        down_btn = QPushButton("▼  Descendre")
        down_btn.setObjectName("editBtn")
        down_btn.clicked.connect(self._move_down)
        rem_btn = QPushButton("✕  Retirer")
        rem_btn.setObjectName("dangerBtn")
        rem_btn.clicked.connect(self._remove_track)
        move_row.addWidget(up_btn)
        move_row.addWidget(down_btn)
        move_row.addStretch()
        move_row.addWidget(rem_btn)
        tl.addLayout(move_row)
        inner_splitter.addWidget(tracks_frame)
        inner_splitter.setSizes([400, 350])
        rl.addWidget(inner_splitter, 1)
        splitter.addWidget(right)
        splitter.setSizes([220, 800])
        layout.addWidget(splitter, 1)

    # ── Data ─────────────────────────────────────────────────────────────────

    def _load_all(self) -> None:
        client = self._cfg.get_client()
        if not client:
            self._status.setText("⚠️  Configurez l'API dans Paramètres API.")
            return
        self._progress.setVisible(True)
        self._status.setText("Chargement…")
        worker = ApiWorker(self._fetch_all, client)
        worker.signals.result.connect(self._on_all_loaded)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(lambda: self._progress.setVisible(False))
        self._pool.start(worker)

    @staticmethod
    def _fetch_all(client) -> tuple:
        playlists = client.get_playlists()
        musics = client.get_all_musics()
        return playlists, musics

    def _on_all_loaded(self, data: tuple) -> None:
        playlists, musics = data
        self._playlists = playlists
        self._all_musics = musics
        self._status.setText(f"{len(playlists)} playlist(s) · {len(musics)} piste(s)")
        self._render_playlists()
        self._render_music_table(self._all_musics)

    def _render_playlists(self) -> None:
        self._pl_list.clear()
        for pl in self._playlists:
            item = QListWidgetItem(f"📁  {pl.get('name', pl.get('id', ''))}")
            item.setData(Qt.ItemDataRole.UserRole, pl)
            self._pl_list.addItem(item)

    def _on_playlist_selected(self, item: QListWidgetItem | None) -> None:
        if not item:
            return
        pl = item.data(Qt.ItemDataRole.UserRole)
        self._selected = pl
        self._save_btn.setEnabled(True)
        self._tracks_lbl.setText(f"Pistes — {pl.get('name', '')}")
        client = self._cfg.get_client()
        if not client:
            return
        self._progress.setVisible(True)
        worker = ApiWorker(client.get_playlist, pl["id"])
        worker.signals.result.connect(self._on_playlist_detail)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(lambda: self._progress.setVisible(False))
        self._pool.start(worker)

    def _on_playlist_detail(self, detail: dict) -> None:
        musics_raw = detail.get("musics") or detail.get("musicIds") or detail.get("ids") or []
        tracks = []
        for item in musics_raw:
            if isinstance(item, str):
                found = next((m for m in self._all_musics if m["id"] == item), None)
                tracks.append(found or {"id": item, "title": item, "artist": ""})
            elif isinstance(item, dict):
                tracks.append(item)
        self._tracks = tracks
        self._render_tracks()

    def _render_music_table(self, musics: list) -> None:
        self._music_table.setRowCount(0)
        for m in musics:
            row = self._music_table.rowCount()
            self._music_table.insertRow(row)
            self._music_table.setItem(row, 0, QTableWidgetItem(m.get("title", "") or "—"))
            self._music_table.setItem(row, 1, QTableWidgetItem(m.get("artist", "") or "—"))
            add_btn = QPushButton("+")
            add_btn.setObjectName("editBtn")
            add_btn.setFixedSize(30, 26)
            add_btn.clicked.connect(lambda _, music=m: self._add_single(music))
            self._music_table.setCellWidget(row, 2, add_btn)

    def _render_tracks(self) -> None:
        self._tracks_table.setRowCount(0)
        for i, t in enumerate(self._tracks, 1):
            row = self._tracks_table.rowCount()
            self._tracks_table.insertRow(row)
            self._tracks_table.setItem(row, 0, QTableWidgetItem(str(i)))
            label = f"{t.get('title', t.get('id', ''))}"
            if t.get("artist"):
                label += f"  —  {t['artist']}"
            self._tracks_table.setItem(row, 1, QTableWidgetItem(label))
            rm = QPushButton("✕")
            rm.setObjectName("dangerBtn")
            rm.setFixedSize(30, 26)
            rm.clicked.connect(lambda _, idx=row: self._remove_at(idx))
            self._tracks_table.setCellWidget(row, 2, rm)

    def _filter_musics(self, query: str) -> None:
        term = query.strip().lower()
        filtered = [m for m in self._all_musics
                    if term in m.get("title", "").lower() or term in m.get("artist", "").lower()] \
            if term else self._all_musics
        self._render_music_table(filtered)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _add_single(self, music: dict) -> None:
        if self._selected is None:
            QMessageBox.warning(self, "Playlist", "Sélectionnez d'abord une playlist.")
            return
        self._tracks.append(music)
        self._render_tracks()

    def _add_selected_to_playlist(self) -> None:
        if self._selected is None:
            QMessageBox.warning(self, "Playlist", "Sélectionnez d'abord une playlist.")
            return
        rows = {i.row() for i in self._music_table.selectedItems()}
        musics_shown = []
        for row in range(self._music_table.rowCount()):
            title = self._music_table.item(row, 0)
            artist = self._music_table.item(row, 1)
            if title:
                t = title.text()
                a = artist.text() if artist else ""
                found = next((m for m in self._all_musics
                              if m.get("title") == t and (not a or m.get("artist") == a)), None)
                musics_shown.append(found)
        for row in sorted(rows):
            m = musics_shown[row] if row < len(musics_shown) else None
            if m:
                self._tracks.append(m)
        self._render_tracks()

    def _remove_at(self, index: int) -> None:
        if 0 <= index < len(self._tracks):
            self._tracks.pop(index)
            self._render_tracks()

    def _remove_track(self) -> None:
        rows = {i.row() for i in self._tracks_table.selectedItems()}
        for row in sorted(rows, reverse=True):
            if 0 <= row < len(self._tracks):
                self._tracks.pop(row)
        self._render_tracks()

    def _move_up(self) -> None:
        rows = sorted({i.row() for i in self._tracks_table.selectedItems()})
        if not rows or rows[0] == 0:
            return
        for r in rows:
            self._tracks[r - 1], self._tracks[r] = self._tracks[r], self._tracks[r - 1]
        self._render_tracks()

    def _move_down(self) -> None:
        rows = sorted({i.row() for i in self._tracks_table.selectedItems()}, reverse=True)
        if not rows or rows[0] >= len(self._tracks) - 1:
            return
        for r in rows:
            self._tracks[r], self._tracks[r + 1] = self._tracks[r + 1], self._tracks[r]
        self._render_tracks()

    def _create_playlist(self) -> None:
        client = self._cfg.get_client()
        if not client:
            QMessageBox.warning(self, "API", "Configurez l'API.")
            return
        name, ok = QInputDialog.getText(self, "Nouvelle playlist", "Nom de la playlist :")
        if not ok or not name.strip():
            return
        worker = ApiWorker(client.create_playlist, name.strip())
        worker.signals.result.connect(lambda _: self._load_all())
        worker.signals.error.connect(self._on_error)
        self._pool.start(worker)

    def _delete_playlist(self) -> None:
        if not self._selected:
            return
        client = self._cfg.get_client()
        if not client:
            return
        reply = QMessageBox.question(self, "Supprimer",
                                     f"Supprimer la playlist « {self._selected.get('name')} » ?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        worker = ApiWorker(client.delete_playlist, self._selected["id"])
        worker.signals.result.connect(lambda _: (setattr(self, "_selected", None), self._load_all()))
        worker.signals.error.connect(self._on_error)
        self._pool.start(worker)

    def _save_playlist(self) -> None:
        if not self._selected:
            return
        client = self._cfg.get_client()
        if not client:
            return
        music_ids = [t["id"] for t in self._tracks if t.get("id")]
        author = self._selected.get("author", "radiodesk")
        worker = ApiWorker(client.save_playlist,
                           self._selected["id"],
                           self._selected.get("name", ""),
                           author, music_ids)
        worker.signals.result.connect(lambda _: self._status.setText("✅ Playlist sauvegardée."))
        worker.signals.error.connect(self._on_error)
        self._pool.start(worker)

    def _on_error(self, msg: str) -> None:
        self._status.setText(f"❌ {msg}")
        self._status.setStyleSheet("color: #dc2626; font-size: 12px; background: transparent; border: none;")
