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
from gemma.config.app_config import LAYOUT_BLOCKS, AppConfig

    

# ===============================
# Bloc état redimensionnable sans cadre blanc
# ===============================
class EtatGraphicsObject(QGraphicsObject):
    
    def __init__(self, code, label, width=250, height=150):
        super().__init__()
        self.code = code
        self.label = label
        self.width = width
        self.height = height
        self.handle_size = AppConfig.HANDLE_SIZE
        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable |
            QGraphicsObject.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.handle_pos = QPointF(width - self.handle_size, height - self.handle_size)
        self._dragging_handle = False

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None):
        

        # Rectangle principal
        painter.setBrush(QBrush(QColor(100, 200, 255)))
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawRect(0, 0, int(self.width), int(self.height))

        # Cercle
        circle_diameter = 24
        painter.setBrush(QBrush(Qt.GlobalColor.transparent))
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawEllipse(4, 5, circle_diameter, circle_diameter)

        # Texte code (dans le cercle)
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.drawText(8, 22, self.code)

        # -------- LABEL AVEC WORD WRAP --------
        text_x = circle_diameter + 12
        text_y = 6
        text_width = self.width - text_x - 6
        text_height = self.height - text_y - 6

        text_rect = QRectF(text_x, text_y, text_width, text_height)

        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            self.label
        )

        # Handle
        painter.setBrush(QBrush(Qt.GlobalColor.darkGray))
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawRect(
            int(self.handle_pos.x()),
            int(self.handle_pos.y()),
            self.handle_size,
            self.handle_size
        )
        def mousePressEvent(self, event):
            if self._on_handle(event.pos()):
                self._dragging_handle = True
            else:
                super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging_handle:
            new_width = max(event.pos().x(), 50)
            new_height = max(event.pos().y(), 30)
            self.width = new_width
            self.height = new_height
            self.handle_pos = QPointF(self.width - self.handle_size, self.height - self.handle_size)
            self.prepareGeometryChange()
            self.update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragging_handle = False
        super().mouseReleaseEvent(event)

    def _on_handle(self, pos):
        return QRectF(self.handle_pos.x(), self.handle_pos.y(), self.handle_size, self.handle_size).contains(pos)

class EtatGroupWithResize(QGraphicsItemGroup):

    def __init__(self, code, label, scene, width=250, height=150):
        super().__init__()
        class CustomRect(QGraphicsRectItem):
            def paint(self, painter, option, widget=None):
                painter.setBrush(QBrush(QColor(100, 200, 255)))
                painter.setPen(QPen(Qt.GlobalColor.black, 1))
                painter.drawRect(self.rect())
                # Ne jamais dessiner le cadre de sélection
                # if option.state & QStyle.State_Selected:
                #     pass
        self.rect = CustomRect(0, 0, width, height)
        self.addToGroup(self.rect)
        circle_diameter = 24
        self.circle = QGraphicsEllipseItem(4, 5, circle_diameter, circle_diameter)
        self.circle.setPen(QPen(Qt.GlobalColor.black, 1))
        self.addToGroup(self.circle)
        self.text_item = QGraphicsTextItem(code)
        self.text_item.setPos(3, 3)
        self.text_item.setDefaultTextColor(Qt.GlobalColor.black)
        self.addToGroup(self.text_item)
        self.text_definition = QGraphicsTextItem(label)
        self.text_definition.setPos(circle_diameter + 8, 3)
        self.text_definition.setDefaultTextColor(Qt.GlobalColor.black)
        self.addToGroup(self.text_definition)
        # Handle de resize (ajouté au groupe)
        self.handle = QGraphicsRectItem(width - self.handle_size, height - self.handle_size, self.handle_size, self.handle_size)
        self.handle.setBrush(QBrush(Qt.GlobalColor.darkGray))
        self.handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.addToGroup(self.handle)
        self.setFlags(
            QGraphicsItemGroup.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItemGroup.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItemGroup.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        # L'event filter sera installé après ajout à la scène


    def sceneEventFilter(self, watched, event):
    
        if watched == self.handle and event.type() == QEvent.Type.GraphicsSceneMouseMove:
            new_width = max(event.scenePos().x() - self.scenePos().x(), 50)
            new_height = max(event.scenePos().y() - self.scenePos().y(), 30)
            # Mise à jour du rectangle unique
            self.rect.prepareGeometryChange()
            self.rect.setRect(0, 0, new_width, new_height)
            self.handle.setRect(new_width - self.handle_size, new_height - self.handle_size, self.handle_size, self.handle_size)
            return True
        return False

    def setPos(self, *args, **kwargs):
        super().setPos(*args, **kwargs)
        # Toujours repositionner le handle dans le coin du rectangle
        rect = self.rect.rect()
        self.handle.setRect(rect.width() - self.handle_size, rect.height() - self.handle_size, self.handle_size, self.handle_size)


class AnimatedRectItem(QGraphicsObject):
    def __init__(self, x, y, w, h):
        super().__init__()

        self.rect = QRectF(0, 0, w, h)
        self.setPos(x, y)

        self._border_color = QColor(255, 255, 255)
        self._background = QColor(180, 180, 180)

        self.animation = QPropertyAnimation(self, b"borderColor")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

    # =========================
    # Obligatoire avec QGraphicsObject
    # =========================
    def boundingRect(self):
        return self.rect

    def paint(self, painter, option, widget):
        painter.setBrush(QBrush(self._background))
        painter.setPen(QPen(self._border_color, 3))
        painter.drawRect(self.rect)

    # =========================
    # Propriété animable
    # =========================
    def getBorderColor(self):
        return self._border_color

    def setBorderColor(self, color):
        self._border_color = color
        self.update()

    borderColor = pyqtProperty(QColor, getBorderColor, setBorderColor)

    # =========================
    # Animations
    # =========================
    def animate_highlight(self):
        self.animation.stop()
        self.animation.setStartValue(self._border_color)
        self.animation.setEndValue(QColor(255, 0, 0))
        self.animation.start()

    def animate_unhighlight(self):
        self.animation.stop()

        # 🔥 Forcer état noir immédiatement
        self._border_color = QColor(0, 0, 0)
        self.update()

       
# =========================================================
# CanvasView
# =========================================================
class CanvasView(QGraphicsView):
    stateDropped = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()

        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Ajouter l'image de fond
        if AppConfig.SHOW_PDF:
            fond_path = "/home/jpvw/Documents/node_appli/gemma_suite/doc/GEMMA-fond.png"
            pixmap = QPixmap(fond_path)
            # Redimensionner le pixmap à la taille du canvas
            canvas_w = AppConfig.CANVAS_WIDTH
            canvas_h = AppConfig.CANVAS_HEIGHT
            pixmap = pixmap.scaled(canvas_w, canvas_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.fond_item = self.scene.addPixmap(pixmap)
            self.fond_item.setZValue(-100)  # Toujours en fond
        
        # print(f"CanvasView: fond chargé depuis {fond_path}")
        self.zones = {}
        self.current_highlight = None

        self.setAcceptDrops(True)  # Activer le drop
        self.setDragMode(QGraphicsView.DragMode.NoDrag)  # Désactiver le rubber band
    
        if not AppConfig.SHOW_PDF:
            self.draw_layout_blocks()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        data = event.mimeData().text()
        if '|' in data:
            code, label = data.split('|', 1)
        else:
            code, label = data, ''
        # Conversion vers coordonnées de la scène
        pos_widget = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        pos_scene = self.mapToScene(pos_widget)
        etat_item = EtatGraphicsObject(code, label)
        etat_item.setPos(pos_scene.x(), pos_scene.y())
        self.scene.addItem(etat_item)

        # Émettre le signal avec le code de l'état
        self.stateDropped.emit(code)

        event.acceptProposedAction()
        
    # ===============================================
    # Redimensionnement
    # ===============================================
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Adapter l'image de fond à la nouvelle taille du canvas
        if hasattr(self, 'fond_item') and self.fond_item is not None:
            fond_path = "/home/jpvw/Documents/node_appli/gemma_suite/doc/GEMMA-fond.png"
            pixmap = QPixmap(fond_path)
            canvas_w = self.viewport().width()
            canvas_h = self.viewport().height()
            pixmap = pixmap.scaled(canvas_w, canvas_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.fond_item.setPixmap(pixmap)
        # Faire correspondre la scène au viewport
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


    # =====================================================
    # Appelée depuis la LISTE
    # =====================================================
    def highlight_zone(self, letter):
        # Toujours enlever l'ancien highlight s'il existe
        if self.current_highlight in self.zones:
            self.zones[self.current_highlight].animate_unhighlight()

        # Mettre à jour l'état
        self.current_highlight = letter

        # Nouveau highlight si nécessaire
        if letter in self.zones:
            self.zones[letter].animate_highlight()

    # =====================================================
    # Construction des blocs
    # =====================================================
    def draw_layout_blocks(self):
        for key, block in LAYOUT_BLOCKS.items():

            rect = AnimatedRectItem(block.x, block.y, block.w, block.h)
            self.scene.addItem(rect)
            self.zones[key] = rect

            circle_diameter = 32

            def draw_content(pos_y):
                #-------------------------------- Circle --------------------------
                circle_x = block.x + 10
                circle_y = pos_y

                circle = QGraphicsEllipseItem(
                    circle_x,
                    circle_y,
                    circle_diameter,
                    circle_diameter
                )
                circle.setPen(QPen(Qt.GlobalColor.darkGray, 2))
                circle.setBrush(QColor(180, 180, 180))
                self.scene.addItem(circle)
                
                #-------------------------------- Letter --------------------------
                letter_item = QGraphicsTextItem(key)
                font = letter_item.font()
                font.setPointSize(16)
                font.setBold(True)
                letter_item.setFont(font)

                letter_width = letter_item.boundingRect().width()
                letter_height = letter_item.boundingRect().height()

                letter_item.setPos(
                    circle_x + (circle_diameter - letter_width) / 2,
                    circle_y + (circle_diameter - letter_height) / 2
                )
                letter_item.setDefaultTextColor(Qt.GlobalColor.darkGray)
                self.scene.addItem(letter_item)

                #-------------------------------- Text --------------------------
                text_item = QGraphicsTextItem(block.text)
                font2 = text_item.font()
                font2.setPointSize(14)
                font2.setBold(True)
                text_item.setFont(font2)

                text_item.setPos(
                    circle_x + circle_diameter + 10,
                    circle_y + 4
                )
                text_item.setDefaultTextColor(Qt.GlobalColor.darkGray)
                self.scene.addItem(text_item)

            top_y = block.y + 10
            bottom_y = block.y + block.h - circle_diameter - 10

            if key == "A":
                draw_content(top_y)
            elif key == "D":
                draw_content(bottom_y)
            elif key == "F":
                draw_content(top_y)
                draw_content(bottom_y)
            else:
                draw_content(top_y)