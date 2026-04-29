from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QComboBox, QFileDialog, QMessageBox, QSlider
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QFont
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from src.controllers.podcast_controller import PodcastController
from src.controllers.emission_controller import EmissionController


class PodcastsPage(QWidget):
    def __init__(self, podcast_ctrl: PodcastController, emission_ctrl: EmissionController) -> None:
        super().__init__()
        self._podcast_ctrl = podcast_ctrl
        self._emission_ctrl = emission_ctrl
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(0.8)
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)
        self._setup_ui()
        self._load_emissions()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        title = QLabel("Gestion des podcasts")
        f = QFont()
        f.setPointSize(18)
        f.setBold(True)
        title.setFont(f)
        layout.addWidget(title)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Émission :"))
        self._emission_combo = QComboBox()
        self._emission_combo.setMinimumWidth(280)
        self._emission_combo.currentIndexChanged.connect(self._load_podcasts)
        selector_row.addWidget(self._emission_combo)
        selector_row.addStretch()

        add_btn = QPushButton("+ Ajouter un podcast")
        add_btn.setObjectName("primaryBtn")
        add_btn.setStyleSheet("")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._on_add)
        selector_row.addWidget(add_btn)
        layout.addLayout(selector_row)

        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget { border: 1px solid #e5e7eb; border-radius: 8px;
                background: white; font-size: 13px; }
            QListWidget::item { padding: 10px 14px; border-bottom: 1px solid #f3f4f6; }
            QListWidget::item:selected { background: #f3ecfa; color: #6B2EA6; }
        """)
        self._list.itemDoubleClicked.connect(self._on_play_selected)
        layout.addWidget(self._list, 1)

        self._empty_label = QLabel("Sélectionnez une émission pour voir ses podcasts.")
        self._empty_label.setStyleSheet("color: #9ca3af; font-size: 13px;")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._empty_label)

        # Lecteur audio
        player_frame = QWidget()
        player_frame.setStyleSheet("QWidget { background: white; border-radius: 8px; border: 1px solid #e5e7eb; }")
        player_layout = QHBoxLayout(player_frame)
        player_layout.setContentsMargins(12, 8, 12, 8)
        player_layout.setSpacing(10)

        self._play_btn = QPushButton("▶ Lire")
        self._play_btn.setFixedWidth(80)
        self._play_btn.setObjectName("playBtn")
        self._play_btn.setStyleSheet("")
        self._play_btn.clicked.connect(self._on_play_pause)
        self._play_btn.setEnabled(False)

        self._stop_btn = QPushButton("■ Stop")
        self._stop_btn.setFixedWidth(70)
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setStyleSheet("")
        self._stop_btn.clicked.connect(self._on_stop)
        self._stop_btn.setEnabled(False)

        self._now_playing = QLabel("Aucune lecture en cours")
        self._now_playing.setStyleSheet("color: #6b7280; font-size: 12px; border: none;")

        vol_label = QLabel("🔊")
        vol_label.setStyleSheet("border: none;")
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setFixedWidth(80)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(80)
        self._vol_slider.valueChanged.connect(lambda v: self._audio_output.setVolume(v / 100.0))

        player_layout.addWidget(self._play_btn)
        player_layout.addWidget(self._stop_btn)
        player_layout.addWidget(self._now_playing, 1)
        player_layout.addWidget(vol_label)
        player_layout.addWidget(self._vol_slider)

        layout.addWidget(player_frame)

    def _load_emissions(self) -> None:
        try:
            emissions = self._emission_ctrl.list_all()
            self._emission_combo.clear()
            self._emission_combo.addItem("— Choisir une émission —", None)
            for em in emissions:
                self._emission_combo.addItem(f"{em.title} ({em.start_dt.strftime('%d/%m')})", em.id)
        except Exception:
            pass

    def _load_podcasts(self) -> None:
        emission_id = self._emission_combo.currentData()
        self._list.clear()
        if not emission_id:
            self._empty_label.setVisible(True)
            self._list.setVisible(False)
            return
        self._empty_label.setVisible(False)
        self._list.setVisible(True)
        try:
            podcasts = self._podcast_ctrl.list_for_emission(emission_id)
            for pod in podcasts:
                item = QListWidgetItem(f"🎵  {pod.title}")
                item.setData(Qt.ItemDataRole.UserRole, pod.id)
                item.setData(Qt.ItemDataRole.UserRole + 1, pod.file_path)
                self._list.addItem(item)
            if not podcasts:
                self._list.addItem("Aucun podcast pour cette émission.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _on_add(self) -> None:
        emission_id = self._emission_combo.currentData()
        if not emission_id:
            QMessageBox.warning(self, "Attention", "Sélectionnez d'abord une émission.")
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Choisir un fichier audio", "",
            "Fichiers audio (*.mp3 *.wav *.ogg *.m4a)"
        )
        if not file_path:
            return
        path = Path(file_path)
        try:
            self._podcast_ctrl.add(
                emission_id=emission_id,
                title=path.stem,
                source_path=path,
            )
            self._load_podcasts()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _on_play_selected(self, item: QListWidgetItem) -> None:
        file_path = item.data(Qt.ItemDataRole.UserRole + 1)
        if not file_path:
            return
        self._player.setSource(QUrl.fromLocalFile(file_path))
        self._player.play()
        self._now_playing.setText(f"▶ {item.text().replace('🎵  ', '')}")
        self._play_btn.setText("⏸ Pause")
        self._play_btn.setEnabled(True)
        self._stop_btn.setEnabled(True)

    def _on_play_pause(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
            self._play_btn.setText("▶ Lire")
        else:
            self._player.play()
            self._play_btn.setText("⏸ Pause")

    def _on_stop(self) -> None:
        self._player.stop()
        self._play_btn.setText("▶ Lire")
        self._now_playing.setText("Aucune lecture en cours")
        self._stop_btn.setEnabled(False)

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self._play_btn.setText("▶ Lire")
            self._now_playing.setText("Aucune lecture en cours")
            self._stop_btn.setEnabled(False)
