import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGroupBox
)

from core.view.canvas_view import CanvasView
from core.view.right_menu import RightMenu
from core.view.palettes.layout_palette import LayoutPalette
from core.controller.layout_controller import LayoutController

from core.view.palettes.states_palette import StatesPalette
from core.controller.states_controller import StatesController

from core.config.app_config import AppConfig


class MainWindow(QMainWindow):

    # Signaux à connecter dans AppController
    layoutModeRequested = pyqtSignal()
    statesModeRequested = pyqtSignal()
    # transitionsModeRequested = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.resize(1100, 650)
        self.app_name = "<Aucune application>"

        # =========================
        # Canvas central
        # =========================
        self.canvas = CanvasView()

        # =========================
        # RightMenu
        # =========================
        self.right_menu = RightMenu()

        # =========================
        # UI setup
        # =========================
        self.setup_ui()

        # =========================
        # Connexion des boutons (signaux)
        # =========================
        self.layout_btn.clicked.connect(self.layoutModeRequested.emit)
        self.states_btn.clicked.connect(self.statesModeRequested.emit)  # à connecter dans AppController
        # self.transitions_btn.clicked.connect(self.transitionsModeRequested.emit)

    

    # =====================================================
    # Activation des modes Layout, States, Transitions              PAS ICI, MAIS DANS LE MODE MANAGER
    # =====================================================
    # Les méthodes d'activation de mode ne sont plus gérées ici, mais via AppController/ModeManager
    # def activate_layout_mode(self):
    #     pass
    # def activate_states_mode(self):
    #     pass

    # =========================
    # Setup UI: LeftMenu et layout principal
    # =========================
    def setup_ui(self):
        # -------- LeftMenu --------
        self.left_menu = QWidget()
        self.left_menu.setFixedWidth(AppConfig.LEFT_MENU_WIDTH)
        left_layout = QVBoxLayout()
        self.left_menu.setLayout(left_layout)

        # Titre principal
        title_label = QLabel("Gemma doctor")
        title_label.setStyleSheet("font-size:18px;font-weight:bold;margin-bottom:12px;")
        left_layout.addWidget(title_label)

        # Groupe Application
        app_group = QGroupBox("Application")
        app_layout = QVBoxLayout()
        self.app_courante = QLabel(f"[{self.app_name}]")
        self.app_courante.setStyleSheet("font-size:13px;font-style:italic;margin-bottom:8px;margin-left:8px;")
        btn_app_charger = QPushButton("Charger")
        btn_app_sauvegarder = QPushButton("Sauvegarder")
        app_layout.addWidget(self.app_courante)
        app_layout.addWidget(btn_app_charger)
        app_layout.addWidget(btn_app_sauvegarder)
        app_group.setLayout(app_layout)
        left_layout.addWidget(app_group)

        # Groupe GEMMA
        gemma_group = QGroupBox("Gemma")
        gemma_layout = QVBoxLayout()
        self.layout_btn = QPushButton("Layout")
        self.states_btn = QPushButton("Etats")
        self.transitions_btn = QPushButton("Transitions")
        gemma_layout.addWidget(self.layout_btn)
        gemma_layout.addWidget(self.states_btn)
        gemma_layout.addWidget(self.transitions_btn)
        gemma_group.setLayout(gemma_layout)
        left_layout.addWidget(gemma_group)

        # Groupe Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        auditer_btn = QPushButton("Auditer")
        generer_btn = QPushButton("Générer")
        actions_layout.addWidget(auditer_btn)
        actions_layout.addWidget(generer_btn)
        actions_group.setLayout(actions_layout)
        left_layout.addWidget(actions_group)

        left_layout.addStretch()

        # -------- Layout principal --------
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.left_menu)
        main_layout.addWidget(self.canvas, 1)  # canvas prend tout l’espace restant
        main_layout.addWidget(self.right_menu)

        wrapper = QWidget()
        wrapper.setLayout(main_layout)
        self.setCentralWidget(wrapper)