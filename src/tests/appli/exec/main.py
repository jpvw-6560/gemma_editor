import sys
from PyQt6.QtWidgets import QApplication

from appli.counter_view import CounterView
from appli.counter_model import CounterModel
from appli.counter_controller import CounterController

# Import des composants (normalement via vos dossiers src/...)

def main():
    app = QApplication(sys.argv)

    # Initialisation des composants
    model = CounterModel()
    view = CounterView()
    
    # Création du lien (Controller)
    controller = CounterController(model, view)

    view.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
