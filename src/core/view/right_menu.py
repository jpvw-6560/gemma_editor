from PyQt6.QtWidgets import QWidget, QVBoxLayout
from core.config.app_config import AppConfig

class RightMenu(QWidget):
    def __init__(self):
        super().__init__()

        # Layout principal du RightMenu
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(5)
        self.setLayout(self.layout)
        self.setFixedWidth(AppConfig.RIGHT_MENU_WIDTH)

        self.current_widget = None  # widget actuellement affiché

    def set_palette_widget(self, widget: QWidget):
        """
        Remplace le widget affiché dans le RightMenu
        par la palette passée en paramètre.
        """
        # Supprimer l’ancien widget
        if self.current_widget:
            self.layout.removeWidget(self.current_widget)
            self.current_widget.setParent(None)
            self.current_widget.deleteLater()
            self.current_widget = None

        # Ajouter le nouveau widget
        if widget:
            self.layout.addWidget(widget)
            self.current_widget = widget
            self.current_widget.show()