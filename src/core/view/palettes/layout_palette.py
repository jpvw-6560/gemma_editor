from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt, QEvent, pyqtSignal
from PyQt6.QtGui import QBrush

from core.model.layout_model import LayoutModel

class LayoutPalette(QWidget):
    # Signaux envoyés au controller
    zoneHovered = pyqtSignal(str)  # lettre de la zone
    zoneLeft = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_model = LayoutModel(self.width(), self.height())

        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("Layout")
        title.setStyleSheet("font-size:18px;font-weight:bold;margin-top:8px;")
        layout.addWidget(title)

        subtitle = QLabel("Zones")
        subtitle.setStyleSheet(
            "font-size:14px;font-weight:bold;margin-top:10px;margin-bottom:4px;margin-left:4px;"
        )
        layout.addWidget(subtitle)

        self.zone_list = QListWidget()
        self.zone_list.setMouseTracking(True)
        self.zone_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.zone_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        for letter, block in self.layout_model.get_blocks().items():
            item = QListWidgetItem(f"Zone {letter}")
            item.setData(Qt.ItemDataRole.UserRole, letter)
            item.setToolTip(block.text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            item.setBackground(QBrush(Qt.GlobalColor.black))
            item.setForeground(QBrush(Qt.GlobalColor.white))
            self.zone_list.addItem(item)

        layout.addWidget(self.zone_list)
        layout.addStretch()

        # ==============================
        # Connexions hover
        # ==============================
        self.zone_list.itemEntered.connect(self._on_item_hover)
        self.zone_list.viewport().installEventFilter(self)

    # ==============================
    # Hover sur un item
    # ==============================
    def _on_item_hover(self, item):
        # 1️⃣ Mettre l’item de la liste en évidence
        self.reset_list_visuals()  # remet les autres à l’état normal

        item.setBackground(Qt.GlobalColor.lightGray)
        item.setForeground(Qt.GlobalColor.black)

        # 2️⃣ Émettre le signal vers le controller
        letter = item.data(Qt.ItemDataRole.UserRole)
        self.zoneHovered.emit(letter)

    # ==============================
    # Event filter pour sortie de la liste
    # ==============================
    def eventFilter(self, obj, event):
        if obj == self.zone_list.viewport() and event.type() == QEvent.Type.Leave:
            self.reset_list_visuals()  # reset visuel liste
            self.zoneLeft.emit()       # signal au controller
        return super().eventFilter(obj, event)
    
    def reset_list_visuals(self):
        """Remet tous les items de la liste à leur couleur par défaut"""
        for i in range(self.zone_list.count()):
            item = self.zone_list.item(i)
            item.setBackground(Qt.GlobalColor.black)  # fond noir
            item.setForeground(Qt.GlobalColor.white)  # texte blanc