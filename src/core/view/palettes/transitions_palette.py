from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

class TransitionsPalette(QWidget):
    def __init__(self, container=None):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Palette Transitions"))
        self.setLayout(layout)