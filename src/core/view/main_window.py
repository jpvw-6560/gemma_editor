import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGroupBox,
    QStackedWidget,
)

from core.view.canvas_view import CanvasView
from core.view.right_menu import RightMenu
from core.view.sidebar import SidebarWidget
from core.view.pages.project_page import ProjectPage

from core.view.palettes.layout_palette import LayoutPalette
from core.controller.layout_controller import LayoutController

from core.view.palettes.states_palette import StatesPalette
from core.controller.states_controller import StatesController

from core.view.palettes.transitions_palette import TransitionsPalette
from core.controller.transitions_controller import TransitionsController

from core.config.app_config import AppConfig


class MainWindow(QMainWindow):

    # ── Signaux projet ────────────────────────────────────────────────────
    newProjectRequested      = pyqtSignal()
    appSaveRequested         = pyqtSignal()
    appLoadRequested         = pyqtSignal()
    loadProjectRequested     = pyqtSignal(str)   # chemin dossier

    # ── Signaux GEMMA ─────────────────────────────────────────────────────
    layoutModeRequested      = pyqtSignal()
    statesModeRequested      = pyqtSignal()
    transitionsModeRequested = pyqtSignal()
    lockToggled              = pyqtSignal(bool)
    auditRequested           = pyqtSignal()

    # ── Signaux Grafcets ──────────────────────────────────────────────────
    grafcetPanelRequested    = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gemma Suite")
        self.resize(1200, 700)
        self.app_name = "<Aucune application>"
        self._is_locked = False

        # widgets partagés (canvas, right_menu) restent intacts
        self.canvas     = CanvasView()
        self.right_menu = RightMenu()

        self._setup_ui()
        self._connect_signals()

    # ─────────────────────────────────────────────────────────────────────
    # Construction UI
    # ─────────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        # ── Sidebar ───────────────────────────────────────────────────────
        self.sidebar = SidebarWidget()

        # ── Stack des pages principales ───────────────────────────────────
        self._page_stack = QStackedWidget()

        # Page 0 : Projet
        self.project_page = ProjectPage()
        self._page_stack.addWidget(self.project_page)   # index 0

        # Page 1 : GEMMA (canvas + right_menu)
        self._gemma_page = self._build_gemma_page()
        self._page_stack.addWidget(self._gemma_page)    # index 1

        # Page 2 : Grafcets (pleine page, ajoutée dynamiquement)
        # → géré via show_fullpage / show_canvas

        # ── Layout racine ─────────────────────────────────────────────────
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self._page_stack)

        wrapper = QWidget()
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.setLayout(main_layout)
        self.setCentralWidget(wrapper)

        # Sélection initiale
        self.sidebar.select("projet")
        self._page_stack.setCurrentIndex(0)

    def _build_gemma_page(self) -> QWidget:
        """Rend la page GEMMA : barre d'outils gauche + canvas + right_menu."""
        page = QWidget()
        page.setObjectName("GemmaPage")

        # ── Barre d'outils GEMMA (mini-left) ─────────────────────────────
        toolbar = QWidget()
        toolbar.setObjectName("GemmaToolbar")
        toolbar.setFixedWidth(AppConfig.LEFT_MENU_WIDTH)
        toolbar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        t_layout = QVBoxLayout(toolbar)
        t_layout.setContentsMargins(8, 8, 8, 8)
        t_layout.setSpacing(6)

        # Groupe Édition GEMMA
        gemma_group = QGroupBox("Édition")
        gemma_gl = QVBoxLayout()
        gemma_gl.setSpacing(4)
        self.layout_btn     = QPushButton("Layout")
        self.states_btn     = QPushButton("États")
        self.transitions_btn = QPushButton("Transitions")
        gemma_gl.addWidget(self.layout_btn)
        gemma_gl.addWidget(self.states_btn)
        gemma_gl.addWidget(self.transitions_btn)
        gemma_group.setLayout(gemma_gl)
        t_layout.addWidget(gemma_group)

        # Groupe Actions
        actions_group = QGroupBox("Actions")
        actions_gl = QVBoxLayout()
        actions_gl.setSpacing(4)
        self.auditer_btn   = QPushButton("Auditer")
        self.simuler_btn   = QPushButton("Simuler")
        self.generer_btn   = QPushButton("Générer")
        self.grafcet_btn   = QPushButton("Grafcets")
        self.lock_btn      = QPushButton("🔒 Verrouiller")
        self.lock_btn.setVisible(False)
        for b, tip in [
            (self.auditer_btn,  "Vérifie la validité du diagramme GEMMA"),
            (self.simuler_btn,  "Simulation de la machine d'état GEMMA"),
            (self.generer_btn,  "Génère les Grafcets depuis le GEMMA"),
            (self.grafcet_btn,  "Gérer les Grafcets du projet"),
            (self.lock_btn,     "Verrouille/déverrouille positions"),
        ]:
            b.setToolTip(tip)
            actions_gl.addWidget(b)
        actions_group.setLayout(actions_gl)
        t_layout.addWidget(actions_group)

        # Nom appli courante
        self.app_courante = QLabel(f"[{self.app_name}]")
        self.app_courante.setStyleSheet(
            "font-size:10px;font-style:italic;color:#7fb3d3;"
        )
        self.app_courante.setWordWrap(True)
        t_layout.addWidget(self.app_courante)

        t_layout.addStretch()

        toolbar.setStyleSheet("""
            #GemmaToolbar { background-color: #2c3e50; }
            QPushButton {
                background-color: #34495e; color: #ecf0f1;
                border: none; border-radius: 4px;
                padding: 6px 8px; font-size: 12px; text-align: left;
            }
            QPushButton:hover { background-color: #2980b9; color: white; }
            QPushButton:pressed { background-color: #1a5276; }
            QGroupBox {
                font-weight: bold; color: #7fb3d3;
                border: none; border-top: 1px solid #3d5a74; border-radius: 0;
                margin-top: 12px; padding-top: 10px; font-size: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; top: 0px; left: 4px;
                padding: 0 4px; background-color: #2c3e50;
            }
            QLabel { color: #bdc3c7; background: transparent; }
        """ + AppConfig.TOOLTIP_QSS)

        # ── Stack interne (canvas normal / pleine-page) ───────────────────
        self._center_stack = QStackedWidget()
        self._center_stack.addWidget(self.canvas)   # index 0

        # ── Layout de la page GEMMA ───────────────────────────────────────
        h = QHBoxLayout(page)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(toolbar)
        h.addWidget(self._center_stack)
        h.addWidget(self.right_menu)
        h.setStretch(0, 0)
        h.setStretch(1, 1)
        h.setStretch(2, 0)

        return page

    # ─────────────────────────────────────────────────────────────────────
    # Connexions
    # ─────────────────────────────────────────────────────────────────────
    def _connect_signals(self):
        # Sidebar → changement de page
        self.sidebar.sectionChanged.connect(self._on_section_changed)

        # Boutons GEMMA
        self.layout_btn.clicked.connect(self.layoutModeRequested.emit)
        self.states_btn.clicked.connect(self.statesModeRequested.emit)
        self.transitions_btn.clicked.connect(self.transitionsModeRequested.emit)
        self.auditer_btn.clicked.connect(self.auditRequested.emit)
        self.lock_btn.clicked.connect(self._toggle_lock)
        self.generer_btn.clicked.connect(self.grafcetPanelRequested.emit)
        self.grafcet_btn.clicked.connect(self.grafcetPanelRequested.emit)

        # ProjectPage
        self.project_page.newProjectRequested.connect(self.newProjectRequested.emit)
        self.project_page.loadProjectRequested.connect(self.loadProjectRequested.emit)

        # Drop états → canvas
        self.states_palette = None
        for child in self.findChildren(QWidget):
            if isinstance(child, StatesPalette):
                self.states_palette = child
                break
        if self.states_palette:
            self.states_palette.stateDropped.connect(self.canvas.handle_state_drop)

    # ─────────────────────────────────────────────────────────────────────
    # Navigation entre sections
    # ─────────────────────────────────────────────────────────────────────
    def _on_section_changed(self, key: str):
        mapping = {"projet": 0, "gemma": 1, "grafcets": 1}
        idx = mapping.get(key, 0)
        self._page_stack.setCurrentIndex(idx)
        if key == "grafcets":
            self.grafcetPanelRequested.emit()

    def navigate_to(self, section: str):
        """Navigation programmatique depuis AppController."""
        self.sidebar.select(section)
        self._on_section_changed(section)

    # ─────────────────────────────────────────────────────────────────────
    # Pleine page (grafcets, simulation…)
    # ─────────────────────────────────────────────────────────────────────
    def show_fullpage(self, widget: QWidget):
        """Affiche widget en pleine page dans la zone canvas."""
        if self._center_stack.count() > 1:
            old = self._center_stack.widget(1)
            self._center_stack.removeWidget(old)
            old.deleteLater()
        self._center_stack.addWidget(widget)
        self._center_stack.setCurrentIndex(1)
        self.right_menu.hide()

    def show_canvas(self):
        """Retourne au canvas GEMMA normal."""
        self._center_stack.setCurrentIndex(0)
        self.right_menu.show()
        if self._center_stack.count() > 1:
            old = self._center_stack.widget(1)
            self._center_stack.removeWidget(old)
            old.deleteLater()

    # ─────────────────────────────────────────────────────────────────────
    # Mise à jour de l'UI selon le projet courant
    # ─────────────────────────────────────────────────────────────────────
    def set_project(self, name: str | None):
        """Met à jour les labels de projet dans la sidebar et la page projet."""
        self.sidebar.set_project_name(name)
        self.project_page.set_current_project(name)
        display = name or "<Aucune application>"
        self.app_name = display
        self.app_courante.setText(f"[{display}]")
        title = f"Gemma Suite — {name}" if name else "Gemma Suite"
        self.setWindowTitle(title)

    def update_app_name(self, name: str):
        """Compatibilité avec l'ancienne API."""
        self.set_project(name)

    # ─────────────────────────────────────────────────────────────────────
    # Style des boutons de mode
    # ─────────────────────────────────────────────────────────────────────
    def set_mode_button_style(self, mode: str):
        active = (
            "QPushButton { background-color:#f1c40f; color:#1a252f; font-weight:bold;"
            " border-radius:4px; padding:6px 8px; text-align:left; }"
            "QPushButton:hover { background-color:#f9e44c; }"
        ) + AppConfig.TOOLTIP_QSS
        inactive = ""

        hide_mode_btns = mode in ("transitions", "auditer", "simulation", "generer", "grafcet")
        self.layout_btn.setVisible(not hide_mode_btns)
        self.states_btn.setVisible(not hide_mode_btns)

        for btn, btn_mode in [
            (self.layout_btn,     "layout"),
            (self.states_btn,     "states"),
            (self.transitions_btn, "transitions"),
        ]:
            btn.setStyleSheet(active if mode == btn_mode else inactive)

        for btn, btn_mode in [
            (self.auditer_btn,  "auditer"),
            (self.simuler_btn,  "simulation"),
            (self.generer_btn,  "generer"),
            (self.grafcet_btn,  "grafcet"),
        ]:
            btn.setStyleSheet(active if mode == btn_mode else inactive)

    # ─────────────────────────────────────────────────────────────────────
    # Verrouillage
    # ─────────────────────────────────────────────────────────────────────
    def _toggle_lock(self):
        self._is_locked = not self._is_locked
        if self._is_locked:
            self.lock_btn.setText("🔓 Déverrouiller")
            self.lock_btn.setStyleSheet("background-color:#c0392b;color:white;font-weight:bold;")
        else:
            self.lock_btn.setText("🔒 Verrouiller")
            self.lock_btn.setStyleSheet("")
        self.lockToggled.emit(self._is_locked)

    def resizeEvent(self, event):
        super().resizeEvent(event)


