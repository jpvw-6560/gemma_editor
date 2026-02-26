from PyQt6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QLabel, QWidget
from PyQt6.QtCore import pyqtSignal

class CounterView(QMainWindow):
    # On définit des signaux pour que le Presenter puisse les écouter
    request_increment = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Architecture Pro PyQt6")
        
        # UI Elements
        self.label = QLabel("Valeur : 0")
        self.btn = QPushButton("Incrémenter")
        
        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.btn)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Connexion interne : le clic bouton émet notre signal personnalisé
        self.btn.clicked.connect(self.request_increment.emit)

    def update_display(self, value):
        self.label.setText(f"Valeur : {value}")
