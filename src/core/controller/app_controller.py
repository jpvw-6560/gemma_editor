# core/controller/app_controller.py

from core.controller.mode_manager import ModeManager

class AppController:

    def __init__(self, view):
        self.view = view

        self.mode_manager = ModeManager(
            canvas=self.view.canvas
        )

        self._connect()

    def _connect(self):
        self.view.layoutModeRequested.connect(
            lambda: self.mode_manager.activate("layout")
        )
        """
        self.view.statesModeRequested.connect(
            lambda: self.mode_manager.activate("states")
        )

        self.view.transitionsModeRequested.connect(
            lambda: self.mode_manager.activate("transitions")
        )
        """