from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QFileDialog, QFrame,
    QDialog, QFormLayout, QDialogButtonBox, QSlider, QProgressBar
)
from PySide6.QtCore import Qt, QUrl, QThreadPool
from PySide6.QtGui import QFont
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from src.lib.api_client import ApiConfigManager
from src.lib.worker import ApiWorker


class _EditDialog(QDialog):
    def __init__(self, music: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Modifier les métadonnées")
        self.setMinimumWidth(420)
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        form = QFormLayout()
        form.setSpacing(10)
        self._title = QLineEdit(music.get("title", ""))
        self._title.setFixedHeight(36)
        self._artist = QLineEdit(music.get("artist", ""))
        self._artist.setFixedHeight(36)
        self._album = QLineEdit(music.get("album", ""))
        self._album.setFixedHeight(36)
        self._genre = QLineEdit(music.get("genre", ""))
        self._genre.setFixedHeight(36)
        self._year = QLineEdit(music.get("year", ""))
        self._year.setFixedHeight(36)
        tags = music.get("tags", [])
        self._tags = QLineEdit(", ".join(tags) if isinstance(tags, list) else str(tags))
        self._tags.setFixedHeight(36)
        form.addRow("Titre", self._title)
        form.addRow("Artiste", self._artist)
        form.addRow("Album", self._album)
        form.addRow("Genre", self._genre)
        form.addRow("Année", self._year)
        form.addRow("Tags", self._tags)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Enregistrer")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        layout.addWidget(btns)

    def get_payload(self) -> dict:
        tags = [t.strip() for t in self._tags.text().replace(";", ",").split(",") if t.strip()]
        return {
            "title": self._title.text().strip(),
            "artist": self._artist.text().strip(),
            "album": self._album.text().strip(),
            "genre": self._genre.text().strip(),
            "year": int(self._year.text()) if self._year.text().strip().isdigit() else None,
            "tags": tags,
        }


class MusicManagerPage(QWidget):
    def __init__(self, config_manager: ApiConfigManager) -> None:
        super().__init__()
        self._cfg = config_manager
        self._musics: list[dict] = []
        self._filtered: list[dict] = []
        self._pool = QThreadPool.globalInstance()
        self._player = QMediaPlayer()
        self._audio = QAudioOutput()
        self._player.setAudioOutput(self._audio)
        self._audio.setVolume(0.8)
        self._playing_id: str | None = None
        self._player.playbackStateChanged.connect(self._on_playback_changed)
        self._setup_ui()
        self._load_musics()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 20)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title = QLabel("Bibliothèque musicale")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Recherche titre / artiste / tag…")
        self._search.setFixedHeight(36)
        self._search.setFixedWidth(280)
        self._search.textChanged.connect(self._filter)
        header.addWidget(self._search)

        reload_btn = QPushButton("↻  Recharger")
        reload_btn.setObjectName("editBtn")
        reload_btn.setFixedHeight(36)
        reload_btn.clicked.connect(self._load_musics)
        header.addWidget(reload_btn)

        upload_btn = QPushButton("⬆  Uploader")
        upload_btn.setObjectName("primaryBtn")
        upload_btn.setFixedHeight(36)
        upload_btn.clicked.connect(self._on_upload)
        header.addWidget(upload_btn)
        layout.addLayout(header)

        # Status bar
        self._status = QLabel("")
        self._status.setStyleSheet("color: #6b7280; font-size: 12px; background: transparent; border: none;")
        layout.addWidget(self._status)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedHeight(4)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # Table
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(["Titre", "Artiste", "Album", "Durée", "Tags", "Actions"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(5, 140)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table, 1)

        # Player bar
        player_frame = QFrame()
        player_frame.setObjectName("statCard")
        player_frame.setFixedHeight(54)
        pr = QHBoxLayout(player_frame)
        pr.setContentsMargins(14, 8, 14, 8)
        pr.setSpacing(10)
        self._play_btn = QPushButton("▶ Lire")
        self._play_btn.setObjectName("playBtn")
        self._play_btn.setFixedWidth(80)
        self._play_btn.setEnabled(False)
        self._play_btn.clicked.connect(self._toggle_play)
        self._stop_btn = QPushButton("■ Stop")
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setFixedWidth(70)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop)
        self._now_lbl = QLabel("Aucune lecture")
        self._now_lbl.setStyleSheet("color: #6b7280; font-size: 12px; border: none; background: transparent;")
        self._vol = QSlider(Qt.Orientation.Horizontal)
        self._vol.setFixedWidth(90)
        self._vol.setRange(0, 100)
        self._vol.setValue(80)
        self._vol.valueChanged.connect(lambda v: self._audio.setVolume(v / 100))
        pr.addWidget(self._play_btn)
        pr.addWidget(self._stop_btn)
        pr.addWidget(self._now_lbl, 1)
        pr.addWidget(QLabel("🔊"))
        pr.addWidget(self._vol)
        layout.addWidget(player_frame)

    # ── Data loading ────────────────────────────────────────────────────────

    def _load_musics(self) -> None:
        client = self._cfg.get_client()
        if not client:
            self._status.setText("⚠️  Configurez l'API dans Paramètres API.")
            return
        self._progress.setVisible(True)
        self._status.setText("Chargement de la bibliothèque…")
        worker = ApiWorker(client.get_all_musics)
        worker.signals.result.connect(self._on_musics_loaded)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(lambda: self._progress.setVisible(False))
        self._pool.start(worker)

    def _on_musics_loaded(self, musics: list) -> None:
        self._musics = musics
        self._status.setText(f"{len(musics)} piste(s) chargée(s).")
        self._filter(self._search.text())

    def _filter(self, query: str = "") -> None:
        term = query.strip().lower()
        if term:
            self._filtered = [
                m for m in self._musics
                if term in m.get("title", "").lower()
                or term in m.get("artist", "").lower()
                or any(term in t.lower() for t in (m.get("tags") or []))
            ]
        else:
            self._filtered = list(self._musics)
        self._render_table()

    def _render_table(self) -> None:
        self._table.setRowCount(0)
        for music in self._filtered:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(music.get("title", "")))
            self._table.setItem(row, 1, QTableWidgetItem(music.get("artist", "") or "—"))
            self._table.setItem(row, 2, QTableWidgetItem(music.get("album", "") or "—"))
            self._table.setItem(row, 3, QTableWidgetItem(self._fmt_duration(music.get("duration", ""))))
            tags = music.get("tags") or []
            self._table.setItem(row, 4, QTableWidgetItem(", ".join(tags) if tags else "—"))

            btn_w = QWidget()
            btn_l = QHBoxLayout(btn_w)
            btn_l.setContentsMargins(4, 2, 4, 2)
            btn_l.setSpacing(4)

            play_btn = QPushButton("▶" if self._playing_id != music.get("id") else "⏸")
            play_btn.setObjectName("playBtn")
            play_btn.setFixedSize(32, 28)
            play_btn.clicked.connect(lambda _, m=music: self._play_from_api(m))

            edit_btn = QPushButton("✏")
            edit_btn.setObjectName("editBtn")
            edit_btn.setFixedSize(32, 28)
            edit_btn.clicked.connect(lambda _, m=music: self._on_edit(m))

            del_btn = QPushButton("🗑")
            del_btn.setObjectName("dangerBtn")
            del_btn.setFixedSize(32, 28)
            del_btn.clicked.connect(lambda _, m=music: self._on_delete(m))

            btn_l.addWidget(play_btn)
            btn_l.addWidget(edit_btn)
            btn_l.addWidget(del_btn)
            self._table.setCellWidget(row, 5, btn_w)

    # ── Actions ─────────────────────────────────────────────────────────────

    def _on_upload(self) -> None:
        client = self._cfg.get_client()
        if not client:
            QMessageBox.warning(self, "API", "Configurez l'API dans Paramètres API.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier audio", "",
                                               "Audio (*.mp3 *.wav *.ogg *.m4a *.flac)")
        if not path:
            return
        self._progress.setVisible(True)
        self._status.setText(f"Upload de {Path(path).name}…")
        worker = ApiWorker(client.upload_music, Path(path))
        worker.signals.result.connect(lambda _: (self._status.setText("✅ Upload réussi."), self._load_musics()))
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(lambda: self._progress.setVisible(False))
        self._pool.start(worker)

    def _on_edit(self, music: dict) -> None:
        client = self._cfg.get_client()
        if not client:
            return
        dlg = _EditDialog(music, parent=self)
        if not dlg.exec():
            return
        payload = dlg.get_payload()
        worker = ApiWorker(client.patch_music, music["id"], payload)
        worker.signals.result.connect(lambda _: (self._status.setText("✅ Métadonnées mises à jour."), self._load_musics()))
        worker.signals.error.connect(self._on_error)
        self._pool.start(worker)

    def _on_delete(self, music: dict) -> None:
        client = self._cfg.get_client()
        if not client:
            return
        reply = QMessageBox.question(self, "Supprimer",
                                     f"Supprimer « {music.get('title', music['id'])} » ?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        worker = ApiWorker(client.delete_music, music["id"])
        worker.signals.result.connect(lambda _: (self._status.setText("✅ Piste supprimée."), self._load_musics()))
        worker.signals.error.connect(self._on_error)
        self._pool.start(worker)

    def _play_from_api(self, music: dict) -> None:
        client = self._cfg.get_client()
        if not client:
            return
        mid = music.get("id", "")
        if self._playing_id == mid:
            self._toggle_play()
            return
        self._stop()
        # Stream via direct URL if the API provides one, otherwise use presigned
        url = f"{client.base_url}/musics/{mid}/stream"
        headers_list = []
        if client.token:
            headers_list = [("Authorization", f"Bearer {client.token}")]
        self._player.setSource(QUrl(url))
        self._player.play()
        self._playing_id = mid
        self._now_lbl.setText(f"▶  {music.get('title', mid)} — {music.get('artist', '')}")
        self._play_btn.setText("⏸ Pause")
        self._play_btn.setEnabled(True)
        self._stop_btn.setEnabled(True)
        self._render_table()

    def _toggle_play(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
            self._play_btn.setText("▶ Lire")
        else:
            self._player.play()
            self._play_btn.setText("⏸ Pause")

    def _stop(self) -> None:
        self._player.stop()
        self._playing_id = None
        self._play_btn.setText("▶ Lire")
        self._play_btn.setEnabled(False)
        self._stop_btn.setEnabled(False)
        self._now_lbl.setText("Aucune lecture")
        self._render_table()

    def _on_playback_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self._stop()

    def _on_error(self, msg: str) -> None:
        self._status.setText(f"❌ {msg}")
        self._status.setStyleSheet("color: #dc2626; font-size: 12px; background: transparent; border: none;")

    @staticmethod
    def _fmt_duration(raw: str) -> str:
        if not raw:
            return "—"
        try:
            secs = int(float(raw))
            return f"{secs // 60}:{secs % 60:02d}"
        except Exception:
            return raw
