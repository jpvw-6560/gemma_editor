from appli.counter_model import CounterModel
from appli.counter_view import CounterView


class CounterController:
    def __init__(self, model, view):
        self.model = model
        self.view = view

        # On connecte le signal de la vue à une action
        self.view.request_increment.connect(self.handle_increment)

    def handle_increment(self):
        # 1. On demande au modèle de changer la donnée
        new_value = self.model.increment()
        # 2. On demande à la vue de se mettre à jour
        self.view.update_display(new_value)
