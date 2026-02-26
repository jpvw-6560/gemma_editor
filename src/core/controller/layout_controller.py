from .base_mode_controller import BaseModeController


class LayoutController(BaseModeController):

    def connect(self):
        print("Layout mode activated")

    def disconnect(self):
        pass
    