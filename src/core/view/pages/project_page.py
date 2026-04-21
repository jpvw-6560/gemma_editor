# core/view/pages/project_page.py
"""
Page « Projet » — section 1 de la sidebar.
Permet de :
  - créer un nouveau projet
  - charger un projet récent (liste)
  - charger un projet depuis le disque (dialog)
  - afficher le projet courant
"""
import json
import os

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QFileDialog, QSizePolicy
)

_SETTINGS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../data/settings.json")
)
_PROJECTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../data/prjets")
)

PAGE_QSS = """
    ProjectPage {
        background-color: #1c2833;
    }
    QLabel#page_title {
        font-size: 20px;
        font-weight: bold;
        color: #ecf0f1;
        padding: 16px 0 4px 0;
    }
    QLabel#section_title {
        font-size: 11px;
        font-weight: bold;
        color: #7fb3d3;
        letter-spacing: 1px;
        padding: 10px 0 2px 0;
    }
    QLabel#current_project {
        font-size: 12px;
        color: #2ecc71;
        font-style: italic;
    }
    QLabel#no_project {
        font-size: 12px;
        color: #7f8c8d;
        font-style: italic;
    }
    QPushButton {
        background-color: #2c3e50;
        color: #ecf0f1;
        border: 1px solid #3d5a74;
        border-radius: 5px;
        padding: 8px 16px;
        font-size: 12px;
    }
    QPushButton:hover { background-color: #2980b9; border-color: #2980b9; }
    QPushButton:pressed { background-color: #1a5276; }
    QPushButton#btn_primary {
        background-color: #2980b9;
        font-weight: bold;
        border: none;
    }
    QPushButton#btn_primary:hover { background-color: #3498db; }
    QListWidget {
        background-color: #17202a;
        border: 1px solid #2c3e50;
        border-radius: 4px;
        color: #bdc3c7;
        font-size: 12px;
    }
    QListWidget::item { padding: 6px 8px; }
    QListWidget::item:hover { background-color: #2c3e50; }
    QListWidget::item:selected { background-color: #2980b9; color: white; }
    QFrame#separator { background-color: #2c3e50; }
"""


class ProjectPage(QWidget):
    """Page d'accueil / gestion du projet."""

    newProjectRequested  = pyqtSignal()
    loadProjectRequested = pyqtSignal(str)   # chemin du dossier projet
    loadAppRequested     = pyqtSignal(str)   # chemin du fichier appli

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ProjectPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(PAGE_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 16, 32, 16)
        root.setSpacing(4)

        # ── Titre ─────────────────────────────────────────────────────────
        title = QLabel("  📁  Projet")
        title.setObjectName("page_title")
        root.addWidget(title)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFixedHeight(1)
        root.addWidget(sep)

        # ── Projet courant ────────────────────────────────────────────────
        root.addWidget(self._section_label("PROJET COURANT"))
        self._current_label = QLabel("— aucun projet ouvert —")
        self._current_label.setObjectName("no_project")
        root.addWidget(self._current_label)

        # ── Boutons principaux ────────────────────────────────────────────
        root.addWidget(self._section_label("ACTIONS"))
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._btn_new = QPushButton("✚  Nouveau projet")
        self._btn_new.setObjectName("btn_primary")
        self._btn_load = QPushButton("📂  Ouvrir…")
        btn_row.addWidget(self._btn_new)
        btn_row.addWidget(self._btn_load)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # ── Projets récents ───────────────────────────────────────────────
        root.addWidget(self._section_label("PROJETS RÉCENTS"))
        self._recent_list = QListWidget()
        self._recent_list.setFixedHeight(180)
        root.addWidget(self._recent_list)

        btn_open_selected = QPushButton("Ouvrir le projet sélectionné")
        btn_open_selected.setFixedWidth(240)
        root.addWidget(btn_open_selected)

        root.addStretch()

        # ── Connexions ────────────────────────────────────────────────────
        self._btn_new.clicked.connect(self.newProjectRequested.emit)
        self._btn_load.clicked.connect(self._on_open_dialog)
        btn_open_selected.clicked.connect(self._on_open_selected)
        self._recent_list.itemDoubleClicked.connect(self._on_item_double_clicked)

        # Charger la liste des projets récents
        self._refresh_recent_list()

    # ── API publique ──────────────────────────────────────────────────────

    def set_current_project(self, name: str | None):
        if name:
            self._current_label.setText(f"✔  {name}")
            self._current_label.setObjectName("current_project")
        else:
            self._current_label.setText("— aucun projet ouvert —")
            self._current_label.setObjectName("no_project")
        self._current_label.style().unpolish(self._current_label)
        self._current_label.style().polish(self._current_label)

    def refresh(self):
        self._refresh_recent_list()

    # ── Privé ─────────────────────────────────────────────────────────────

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("section_title")
        return lbl

    def _refresh_recent_list(self):
        self._recent_list.clear()
        if not os.path.isdir(_PROJECTS_DIR):
            return
        projects = sorted(
            [d for d in os.listdir(_PROJECTS_DIR)
             if os.path.isdir(os.path.join(_PROJECTS_DIR, d))],
            key=lambda d: os.path.getmtime(os.path.join(_PROJECTS_DIR, d)),
            reverse=True
        )
        for name in projects:
            item = QListWidgetItem(f"  📁  {name}")
            item.setData(Qt.ItemDataRole.UserRole, os.path.join(_PROJECTS_DIR, name))
            self._recent_list.addItem(item)

        # Éventuellement charger le dernier projet depuis settings.json
        last = self._read_last_project()
        if last:
            for i in range(self._recent_list.count()):
                it = self._recent_list.item(i)
                if it.data(Qt.ItemDataRole.UserRole) == last:
                    self._recent_list.setCurrentItem(it)
                    break

    def _read_last_project(self) -> str | None:
        try:
            with open(_SETTINGS_PATH, encoding="utf-8") as f:
                return json.load(f).get("last_project")
        except Exception:
            return None

    def _on_open_dialog(self):
        path = QFileDialog.getExistingDirectory(
            self, "Ouvrir un projet", _PROJECTS_DIR
        )
        if path:
            self.loadProjectRequested.emit(path)

    def _on_open_selected(self):
        item = self._recent_list.currentItem()
        if item:
            self.loadProjectRequested.emit(item.data(Qt.ItemDataRole.UserRole))

    def _on_item_double_clicked(self, item: QListWidgetItem):
        self.loadProjectRequested.emit(item.data(Qt.ItemDataRole.UserRole))
