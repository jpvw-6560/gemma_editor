from PyQt6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsTextItem,
    QGraphicsObject,
    QGraphicsItemGroup,
    QGraphicsItem
)

from PyQt6.QtGui import QColor, QPen, QBrush, QPixmap, QFontMetrics
from PyQt6.QtCore import Qt, QEvent, QPropertyAnimation, pyqtProperty, QRectF, QPointF, QEasingCurve, pyqtSignal
from core.config.app_config import LAYOUT_BLOCKS, AppConfig

import os 

class CanvasView(QGraphicsView):

    stateDropped = pyqtSignal(str, str, QPointF)
    zoneHovered = pyqtSignal(str)
    canvasClicked = pyqtSignal(QPointF)

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

    # ===== EMISSION UNIQUEMENT =====

    def dropEvent(self, event):
        code = event.mimeData().data("code")
        label = event.mimeData().data("label")
        pos = self.mapToScene(event.pos())

        self.stateDropped.emit(code, label, pos)

    # ===== EXECUTION GRAPHIQUE =====

    def add_state_graphic(self, state_id, pos):
        item = EtatGraphicsObject(state_id)
        item.setPos(pos)
        self.scene.addItem(item)

    def highlight_zone(self, letter):
        for key, rect in self.zones.items():
            if key == letter:
                rect.animate_highlight()
            else:
                rect.animate_unhighlight()