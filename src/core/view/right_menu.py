from PyQt6.QtWidgets import QWidget, QVBoxLayout
from core.config.app_config import AppConfig

class RightMenu(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent) 
        self.layout = QVBoxLayout(self)
        self.setFixedWidth(AppConfig.RIGHT_MENU_WIDTH)
      
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.current_palette = None

    def set_palette(self, palette):

        # Supprimer l’ancienne palette si elle existe
        if self.current_palette:
            self.layout.removeWidget(self.current_palette)
            self.current_palette.deleteLater()
            self.current_palette = None

        if palette:
            # Ajouter la nouvelle palette en haut
            self.layout.insertWidget(0, palette)
            self.current_palette = palette


