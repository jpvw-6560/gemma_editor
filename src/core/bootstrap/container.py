# core/bootstrap/container.py

# from core.model.app_model import AppModel
from core.view.main_window import MainWindow
from core.controller.app_controller import AppController    


class Container:

    def __init__(self):
        # self.model = AppModel()
        self.main_window = MainWindow()
        self.app_controller = AppController(
            view=self.main_window
        )