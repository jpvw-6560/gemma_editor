from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QEvent
from PyQt6.QtGui import QDrag, QColor, QBrush, QPainter, QCursor, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout,
    QListWidget, QListWidgetItem
)

from core.config.app_config import AppConfig
from core.model.states_model import StatesModel


class StatesListWidget(QListWidget):

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
            item = self.itemAt(event.pos())
            if item:
                self.setCurrentItem(item)
                self.startDrag(Qt.DropAction.MoveAction)
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().mouseMoveEvent(event)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return

        mime_data = QMimeData()
        code = item.data(Qt.ItemDataRole.UserRole)
        label = item.toolTip()
        mime_data.setText(f"{code}|{label}")

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        pixmap = QPixmap(60, 40)
        pixmap.fill(QColor(255, 250, 240))
        painter = QPainter(pixmap)
        painter.setPen(QColor(180, 180, 180))
        painter.drawRect(0, 0, 59, 39)
        painter.end()
        drag.setPixmap(pixmap)

        drag.exec(supportedActions)


class StatesPalette(QWidget):

    # 🔥 Signaux MVC
    resetRequested = pyqtSignal()
    loadRequested = pyqtSignal()
    saveRequested = pyqtSignal()
    # stateRemovedFromCanvas = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Etats")
        layout.addWidget(title)

        self.states_list = StatesListWidget()
        self.states_list.setDragEnabled(True)
        self.states_list.setMouseTracking(True)
        layout.addWidget(self.states_list)

        #self.fill_etat_list()

        self.btn_reinit = QPushButton("Réinitialiser")
        self.btn_charger = QPushButton("Ouvrir")
        self.btn_sauvegarder = QPushButton("Enregistrer")

        layout.addWidget(self.btn_reinit)
        layout.addWidget(self.btn_charger)
        layout.addWidget(self.btn_sauvegarder)
        layout.addStretch()

        # Connexions boutons
        self.btn_reinit.clicked.connect(self.resetRequested.emit)
        self.btn_charger.clicked.connect(self.loadRequested.emit)
        self.btn_sauvegarder.clicked.connect(self.saveRequested.emit)

        # Hover
        self.states_list.itemEntered.connect(self.on_item_hover)
        self.states_list.viewport().installEventFilter(self)

    def fill_etat_list(self, etats):
        self.states_list.clear()
        for etat in reversed(etats):
            item = QListWidgetItem(f"{etat.code} - {etat.label}")
            item.setData(Qt.ItemDataRole.UserRole, etat.code)
            self.states_list.addItem(item)

    def remove_state_item(self, code):
        for i in range(self.states_list.count()):
            item = self.states_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == code:
                self.states_list.takeItem(i)
                break

    def on_item_hover(self, item):
        self.reset_list_visuals()
        item.setBackground(QBrush(Qt.GlobalColor.lightGray))
        item.setForeground(QBrush(Qt.GlobalColor.black))

    def eventFilter(self, obj, event):
        if obj == self.states_list.viewport() and event.type() == QEvent.Type.Leave:
            self.reset_list_visuals()
        return super().eventFilter(obj, event)

    def reset_list_visuals(self):
        for i in range(self.states_list.count()):
            item = self.states_list.item(i)
            item.setBackground(QBrush(Qt.GlobalColor.black))
            item.setForeground(QBrush(Qt.GlobalColor.white))