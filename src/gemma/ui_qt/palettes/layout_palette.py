from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QColor, QBrush
from gemma.config.app_config import LAYOUT_BLOCKS


class LayoutPalette(QWidget):
    def __init__(self, canvas=None):
        super().__init__()

        self.canvas = canvas
        layout = QVBoxLayout()

        # =========================
        # Titre
        # =========================
        title = QLabel("Layout")
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold; margin-top: 8px;"
        )
        layout.addWidget(title)

        subtitle = QLabel("Zones")
        subtitle.setStyleSheet(
            "font-size: 14px; font-weight: bold; "
            "margin-top: 10px; margin-bottom: 4px; margin-left: 4px;"
        )
        layout.addWidget(subtitle)

        # =========================
        # Liste des zones
        # =========================
        self.zone_list = QListWidget()
        self.zone_list.setMouseTracking(True)  # 🔥 indispensable
        self.zone_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.zone_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        for letter, block in LAYOUT_BLOCKS.items():
            item = QListWidgetItem(f"Zone {letter}")
            item.setData(Qt.ItemDataRole.UserRole, letter)
            item.setToolTip(block.text)

            # ⚡ Important : autoriser la couleur de fond
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

            # couleur de fond noire initiale
            item.setBackground(QBrush(Qt.GlobalColor.black))

            self.zone_list.addItem(item)

        layout.addWidget(self.zone_list)
        layout.addStretch()
        self.setLayout(layout)

        # =========================
        # Connexions hover
        # =========================
        self.zone_list.itemEntered.connect(self.on_item_hover)
        self.zone_list.viewport().installEventFilter(self)

    # =====================================================
    # Hover sur un item
    # =====================================================
    def on_item_hover(self, item):
        letter = item.data(Qt.ItemDataRole.UserRole)

        if self.canvas:
            self.canvas.highlight_zone(letter)

        # Reset seulement la liste
        self.reset_list_visuals()

        item.setBackground(QBrush(Qt.GlobalColor.lightGray))
        item.setForeground(QBrush(Qt.GlobalColor.black))

    # =====================================================
    # Sortie de la liste
    # =====================================================
    def on_leave(self, event):
        # Canvas reset
        if self.canvas:
            self.canvas.highlight_zone(None)

        # Liste reset
        for i in range(self.zone_list.count()):
            self.zone_list.item(i).setBackground(QBrush(Qt.GlobalColor.black))
            self.zone_list.item(i).setForeground(QBrush(Qt.GlobalColor.white))

        # Appeler le leaveEvent original
        # self.zone_list.viewport().leaveEvent(event)

    # =====================================================
    # Event filter pour détecter la sortie du widget
    # =====================================================
    def eventFilter(self, obj, event):
        if obj == self.zone_list.viewport():
            if event.type() == QEvent.Type.Leave:
                # Reset canvas
                if self.canvas:
                    self.canvas.highlight_zone(None)

                # Reset liste
                self.reset_list_visuals()

        return super().eventFilter(obj, event)

    # =====================================================
    # Reset du hover
    # =====================================================
    def reset_hover(self):
        # Canvas reset
        if self.canvas:
            self.canvas.highlight_zone(None)

        # Liste reset
        for i in range(self.zone_list.count()):
            item = self.zone_list.item(i)
            item.setBackground(QBrush(Qt.GlobalColor.black))
            item.setForeground(QBrush(Qt.GlobalColor.white))

    # =====================================================
    # Reset list visuals
    # =====================================================
    def reset_list_visuals(self):
        for i in range(self.zone_list.count()):
            item = self.zone_list.item(i)
            item.setBackground(QBrush(Qt.GlobalColor.black))
            item.setForeground(QBrush(Qt.GlobalColor.white))