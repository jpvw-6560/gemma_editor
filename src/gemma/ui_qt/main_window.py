from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox
from gemma.ui_qt.canvas.canvas_view import CanvasView
from gemma.ui_qt.presenters.canvas_presenter import CanvasPresenter
from gemma.ui_qt.right_menu import RightMenu

from gemma.infrastructure.router import Router
from gemma.infrastructure.routes import register_routes

# Palettes
from gemma.ui_qt.palettes.layout_palette import LayoutPalette
from gemma.ui_qt.palettes.etats_palette import EtatsPalette
from gemma.ui_qt.palettes.transitions_palette import TransitionsPalette

# Controllers
from gemma.ui_qt.controllers.layout_controller import LayoutController
from gemma.ui_qt.controllers.etats_controller import EtatsController
from gemma.ui_qt.controllers.transitions_controller import TransitionsController

from gemma.config.app_config import AppConfig

class MainWindow(QMainWindow):
    def __init__(self, container):
        super().__init__()
        self.setWindowTitle("GEMMA Editor")
        self.resize(1100, 650)

        # Canvas central
        self.canvas = CanvasView()
        self.presenter = CanvasPresenter(self.canvas.scene, container.event_bus)

        # Router
        self.router = Router()
        register_routes(self.router, self.canvas)

        # LeftMenu  dynamique
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

        # Container 'Gemma' avec boutons
        gemma_group = QGroupBox("Gemma")
        gemma_layout = QVBoxLayout()

        btn_layout = QPushButton("Layout")
        btn_etats = QPushButton("Etats")
        btn_transitions = QPushButton("Transitions")

        btn_layout.clicked.connect(lambda: self.router.navigate("layout", container, self.right_menu))
        btn_etats.clicked.connect(lambda: self.router.navigate("etats", container, self.right_menu))
        btn_transitions.clicked.connect(lambda: self.router.navigate("transitions", container, self.right_menu))
        
        gemma_layout.addWidget(btn_layout)
        gemma_layout.addWidget(btn_etats)
        gemma_layout.addWidget(btn_transitions)

        gemma_group.setLayout(gemma_layout)
        left_layout.addWidget(gemma_group)

        # Container 'Actions' avec boutons
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        btn_auditer = QPushButton("Auditer")
        btn_generer = QPushButton("Générer")
        actions_layout.addWidget(btn_auditer)
        actions_layout.addWidget(btn_generer)
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