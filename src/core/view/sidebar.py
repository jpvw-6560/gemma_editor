# core/view/sidebar.py
"""
Sidebar de navigation principale (menu gauche avec sections cliquables).
Émet le signal `sectionChanged(str)` quand l'utilisateur change de section.
Sections : "projet" | "gemma" | "grafcets"
"""
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy


SIDEBAR_QSS = """
    SidebarWidget {
        background-color: #1a252f;
        border-right: 2px solid #2980b9;
    }
    QPushButton {
        background-color: transparent;
        color: #bdc3c7;
        border: none;
        border-radius: 6px;
        padding: 10px 8px;
        font-size: 12px;
        text-align: left;
    }
    QPushButton:hover {
        background-color: #2c3e50;
        color: #ecf0f1;
    }
    QPushButton[active="true"] {
        background-color: #2980b9;
        color: white;
        font-weight: bold;
    }
    QLabel#app_title {
        color: #2980b9;
        font-size: 14px;
        font-weight: bold;
        padding: 12px 8px 4px 8px;
    }
    QLabel#section_label {
        color: #566573;
        font-size: 9px;
        font-weight: bold;
        padding: 8px 8px 2px 8px;
        letter-spacing: 1px;
    }
    QLabel#project_name {
        color: #7fb3d3;
        font-size: 10px;
        font-style: italic;
        padding: 0px 8px 6px 8px;
    }
"""


class SidebarWidget(QWidget):
    sectionChanged = pyqtSignal(str)  # "projet" | "gemma" | "grafcets"

    _SECTIONS = [
        ("projet",    "📁",  "Projet"),
        ("gemma",     "🔷",  "GEMMA"),
        ("grafcets",  "📊",  "Grafcets"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarWidget")
        self.setFixedWidth(140)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(SIDEBAR_QSS)

        self._buttons: dict[str, QPushButton] = {}
        self._current = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 8)
        layout.setSpacing(0)

        # Titre
        title = QLabel("Gemma Suite")
        title.setObjectName("app_title")
        layout.addWidget(title)

        # Nom du projet courant
        self._project_label = QLabel("— aucun projet —")
        self._project_label.setObjectName("project_name")
        self._project_label.setWordWrap(True)
        layout.addWidget(self._project_label)

        # Séparateur visuel
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#2c3e50; margin: 4px 0;")
        layout.addWidget(sep)

        # Boutons de navigation
        nav_label = QLabel("NAVIGATION")
        nav_label.setObjectName("section_label")
        layout.addWidget(nav_label)

        for key, icon, label in self._SECTIONS:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setCheckable(False)
            btn.setProperty("active", False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._select(k))
            self._buttons[key] = btn
            layout.addWidget(btn)

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Version
        version_label = QLabel("v0.2.0")
        version_label.setStyleSheet("color:#566573; font-size:9px; padding:4px 8px;")
        layout.addWidget(version_label)

    def set_project_name(self, name: str):
        """Met à jour le label du projet affiché sous le titre."""
        self._project_label.setText(name or "— aucun projet —")

    def select(self, key: str):
        """Sélectionne programmatiquement une section sans émettre de signal."""
        self._apply_selection(key)

    def _select(self, key: str):
        self._apply_selection(key)
        self.sectionChanged.emit(key)

    def _apply_selection(self, key: str):
        if self._current == key:
            return
        # Désactiver l'ancien bouton
        if self._current in self._buttons:
            old = self._buttons[self._current]
            old.setProperty("active", False)
            old.style().unpolish(old)
            old.style().polish(old)
        # Activer le nouveau
        self._current = key
        if key in self._buttons:
            btn = self._buttons[key]
            btn.setProperty("active", True)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
