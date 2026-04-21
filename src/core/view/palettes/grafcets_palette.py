"""
GrafcetsPalette — Palette du menu droit pour gérer les Grafcets du projet.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal


class GrafcetsPalette(QWidget):
    """
    Palette affichée dans le menu droit lors du clic sur le bouton « Grafcets ».
    Propose trois actions :
      • showAllRequested      → affiche les derniers Grafcets générés
      • generateRequested     → génère les 3 Grafcets depuis le GEMMA validé
      • newGrafcetRequested   → ouvre l'éditeur pour un Grafcet personnalisé
    """
    showAllRequested    = pyqtSignal()
    generateRequested   = pyqtSignal()
    newGrafcetRequested = pyqtSignal()

    def __init__(self, has_last_grafcets: bool = False, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(8)

        title = QLabel("Grafcets")
        title.setStyleSheet("font-weight: bold; font-size: 13px; margin-bottom: 4px;")
        layout.addWidget(title)

        _active_btn_style = (
            "QPushButton { background:#2471a3; color:white; font-weight:bold; "
            "padding:5px 8px; border:none; border-radius:4px; }"
            "QPushButton:hover { background:#2980b9; }"
            "QPushButton:pressed { background:#1a5276; }"
        )
        _disabled_btn_style = (
            "QPushButton { background:#555; color:#888; "
            "padding:5px 8px; border:none; border-radius:4px; }"
        )
        _normal_btn_style = (
            "QPushButton { background:#34495e; color:white; font-weight:bold; "
            "padding:5px 8px; border:none; border-radius:4px; }"
            "QPushButton:hover { background:#4a6278; }"
            "QPushButton:pressed { background:#2c3e50; }"
        )

        btn_all = QPushButton("👁  Tous")
        btn_all.setToolTip("Afficher les Grafcets générés lors de la dernière génération")
        btn_all.setEnabled(has_last_grafcets)
        btn_all.setStyleSheet(_active_btn_style if has_last_grafcets else _disabled_btn_style)
        btn_all.clicked.connect(self.showAllRequested.emit)
        layout.addWidget(btn_all)

        btn_gen = QPushButton("⚙  Générer depuis GEMMA")
        btn_gen.setToolTip(
            "Génère automatiquement les 3 Grafcets (GS, GC, GPN)\n"
            "à partir du GEMMA validé"
        )
        btn_gen.setStyleSheet(_normal_btn_style)
        btn_gen.clicked.connect(self.generateRequested.emit)
        layout.addWidget(btn_gen)

        btn_new = QPushButton("✏  Nouveau Grafcet")
        btn_new.setToolTip("Ouvrir l'éditeur pour créer un Grafcet personnalisé")
        btn_new.setStyleSheet(_normal_btn_style)
        btn_new.clicked.connect(self.newGrafcetRequested.emit)
        layout.addWidget(btn_new)

        layout.addStretch()
