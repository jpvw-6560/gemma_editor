# core/controller/app_controller.py

from core.controller.mode_manager import ModeManager


class AppController:

    def __init__(self, view):
        self.view = view

        # Création du ModeManager
        self.mode_manager = ModeManager(
            canvas=self.view.canvas,
            right_menu=self.view.right_menu
        )

        # Connexion des signaux de MainWindow aux méthodes d'activation
        self.view.layoutModeRequested.connect(self.activate_layout_mode)
        self.view.statesModeRequested.connect(self.activate_states_mode)
        # self.view.transitionsModeRequested.connect(self.activate_transitions_mode)

        # Mode par défaut
        self.mode_manager.activate("layout")

        # Chargement layout initial
        if self.mode_manager.current_controller:
            self.mode_manager.current_controller.load_layout()

    # -----------------------------
    # Appelé par menus / toolbar
    # -----------------------------
    def activate_layout_mode(self):
        self.mode_manager.activate("layout")

    def activate_states_mode(self):
        self.mode_manager.activate("states")