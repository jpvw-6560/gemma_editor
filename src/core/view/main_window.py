import os, json
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QPropertyAnimation
from PyQt6.QtWidgets import (   QMainWindow, 
                                QWidget, 
                                QVBoxLayout, 
                                QHBoxLayout, 
                                QPushButton, 
                                QLabel, 
                                QGroupBox, 
                                QFileDialog, 
                                QMessageBox,
                                QDialog, 
                                QGraphicsOpacityEffect
                            )
from PyQt6.QtCore import pyqtSignal
from core.view.canvas_view import CanvasView
from core.view.right_menu import RightMenu

#from core.router import Router
#from core.routes import routes

# Toast messages
from core.services.toast.toast import MsgToast

# Palettes
from core.view.palettes.layout_palette import LayoutPalette
#from core.view.palettes.etats_palette import EtatsPalette
#from core.view.palettes.transitions_palette import TransitionsPalette

# Controllers
from core.controller.layout_controller import LayoutController
#from core.controller.etats_controller import EtatsController
#from core.controller.transitions_controller import TransitionsController

# from core.view.canvas_view import EtatGraphicsObject

from core.config.app_config import AppConfig

class MainWindow(QMainWindow):

    layoutModeRequested = pyqtSignal()
    # statesModeRequested = pyqtSignal()
    # transitionsModeRequested = pyqtSignal()

    def __init__(self):
        super().__init__()
        
        self.resize(1100, 650)
        self.app_name = "<Aucune application>"

        # Canvas central
        self.canvas = CanvasView()
        #-----------------------------------------------------------------
        # Menu dynamique
        #-----------------------------------------------------------------
        self.setup_ui()

   
        self.layout_btn.clicked.connect(
            self.layoutModeRequested.emit
        )   
        # self.states_btn.clicked.connect(
        #     self.statesModeRequested.emit
        # )
        # self.transitions_btn.clicked.connect(
        #     self.transitionsModeRequested.emit
        # )
        #-----------------------------------------------------------------
    
    def setup_ui(self):# LeftMenu  dynamique
        self.left_menu = QWidget()
        self.left_menu.setFixedWidth(AppConfig.LEFT_MENU_WIDTH)
        left_layout = QVBoxLayout()
        self.left_menu.setLayout(left_layout)

        # RightMenu dynamique
        self.right_menu = RightMenu()
 

        # Titre principal
        title_label = QLabel("Gemma doctor")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 12px;")
        left_layout.addWidget(title_label)

        # Groupe Application : Charger/Sauvegarder
        app_group = QGroupBox("Application")
        app_layout = QVBoxLayout()

        self.app_courante = QLabel(f"[{self.app_name}]")
        self.app_courante.setStyleSheet("font-size: 13px; font-style: italic; margin-bottom: 8px; margin-left: 8px;")

        btn_app_charger = QPushButton("Charger")
        btn_app_sauvegarder = QPushButton("Sauvegarder")

        app_layout.addWidget(self.app_courante)
        app_layout.addWidget(btn_app_charger)
        app_layout.addWidget(btn_app_sauvegarder)
        app_group.setLayout(app_layout)

        left_layout.addWidget(app_group)
        
        # Container 'Gemma' avec boutons
        gemma_group = QGroupBox("Gemma")
        gemma_layout = QVBoxLayout()

        self.layout_btn = QPushButton("Layout")
        self.states_btn = QPushButton("Etats")
        self.transitions_btn = QPushButton("Transitions")

        #self.layout_btn.clicked.connect(lambda: activate_mode("layout"))
        #self.states_btn.clicked.connect(lambda: activate_mode("etats"))
        #self.transitions_btn.clicked.connect(lambda: activate_mode("transitions"))
        #btn_app_charger.clicked.connect(self.handle_charger_app)
        #btn_app_sauvegarder.clicked.connect(self.sauvegarder_application)
        
        gemma_layout.addWidget(self.layout_btn)
        gemma_layout.addWidget(self.states_btn)
        gemma_layout.addWidget(self.transitions_btn)

        gemma_group.setLayout(gemma_layout)
        left_layout.addWidget(gemma_group)

        # Container 'Actions' avec boutons
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        auditer_btn = QPushButton("Auditer")
        generer_btn = QPushButton("Générer")
        actions_layout.addWidget(auditer_btn)
        actions_layout.addWidget(generer_btn)
        actions_group.setLayout(actions_layout)
        left_layout.addWidget(actions_group)

        left_layout.addStretch()

        # Layout principal
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.left_menu)
        main_layout.addWidget(self.canvas, 1)  # Canvas prend tout l'espace restant
        main_layout.addWidget(self.right_menu)

        wrapper = QWidget()
        wrapper.setLayout(main_layout)
        self.setCentralWidget(wrapper)
        # self.charger_derniere_application() 