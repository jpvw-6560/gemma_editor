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

from PyQt6.QtGui import QColor, QPen, QBrush, QPixmap, QFontMetrics, QPainter, QCursor
from PyQt6.QtCore import Qt, QEvent, QPropertyAnimation, pyqtProperty, QRectF, QPointF, QEasingCurve, pyqtSignal
from core.config.app_config import AppConfig

import os 


# ===============================
# Bloc état redimensionnable sans cadre blanc
# ===============================
class EtatGraphicsObject(QGraphicsObject):
    # Signal pour demander la suppression du bloc
    deleteRequested = pyqtSignal(str)

    
    def __init__(self, code, label, width=250, height=150):
        super().__init__()
        self.code = code
        self.label = label
        self.width_ref = width
        self.height_ref = height
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
        self.handle_visible = True  # Par défaut, visible
        self._border_color = Qt.GlobalColor.black  # Bordure noire par défaut
        self._states_interactive = True  # Par défaut, le clic droit est actif

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None):
        # Rectangle principal
        painter.setBrush(QBrush(QColor(100, 200, 255)))
        painter.setPen(QPen(self._border_color, 2))
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

        # Handle (affiché seulement si handle_visible)
        if self.handle_visible:
            painter.setBrush(QBrush(Qt.GlobalColor.darkGray))
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawRect(
                int(self.handle_pos.x()),
                int(self.handle_pos.y()),
                self.handle_size,
                self.handle_size
            )

    def set_handle_visible(self, visible: bool):
        self.handle_visible = visible
        self.update()
            
    def mousePressEvent(self, event):
        # Accès à la vue principale (CanvasView) via la scène
        canvas_view = None
        if self.scene() and self.scene().views():
            canvas_view = self.scene().views()[0]
        if canvas_view:
            print(f"Mouse press on state : {canvas_view.action_for_states}")
            action_for_states = canvas_view.action_for_states
        else:
            print("Mouse press on state : (vue non trouvée)")
            action_for_states = None
        if event.button() == Qt.MouseButton.RightButton:
            if not action_for_states:
                print("Clic droit désactivé sur les blocs état")
                # Si le clic droit est désactivé, on laisse le comportement par défaut
                super().mousePressEvent(event)
                return
            # Mettre en évidence la bordure spécifique état
            self.animate_state_block_highlight()
            # Menu contextuel
            from PyQt6.QtWidgets import QMenu
            menu = QMenu()
            action_delete = menu.addAction('Supprimer')
            action = menu.exec(event.screenPos())
            if action == action_delete:
                # Émettre le signal pour suppression
                self.deleteRequested.emit(self.code)
            # Désélectionner la bordure après
            self.animate_state_block_unhighlight()
        else:
            if self._on_handle(event.pos()):
                self._dragging_handle = True
            else:
                super().mousePressEvent(event)
        
    def animate_state_block_highlight(self):
        self._border_color = Qt.GlobalColor.red
        self.update()

    def animate_state_block_unhighlight(self):
        self._border_color = Qt.GlobalColor.black
        self.update()

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
        print(f"Mouse release on state : dragging_handle={self._dragging_handle}")
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

        self.rect = QRectF(x, y, w, h)
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


class LayoutBlockGraphicsObject(QGraphicsObject):

    def __init__(self, key, block):
        super().__init__()

        self.key = key
        self.block = block
        self.circle_diameter = 20

        # Position globale
        self.setPos(block.x, block.y)

        # Rectangle animé
        self.rect_item = AnimatedRectItem(0, 0, block.w, block.h)
        self.rect_item.setParentItem(self)

        # Contenu
        self.content_items = []
        self._create_content()
        self._update_geometry()

    # -------------------------
    # Obligatoire
    # -------------------------
    def boundingRect(self):
        return QRectF(0, 0, self.block.w, self.block.h)

    def paint(self, painter, option, widget=None):
        pass  # tout est géré par les sous-items

    # -------------------------
    # Création contenu
    # -------------------------
    def _create_content(self):
        self.content_items = []
        padding = 8
        # Pour chaque zone, on place le contenu en haut ou en bas
        if self.key == "A":
            positions = ["top"]
        elif self.key == "D":
            positions = ["bottom"]
        elif self.key == "F":
            positions = ["top", "bottom"]
        else:
            positions = ["top"]

        for pos in positions:
            circle = QGraphicsEllipseItem(self)
            circle.setPen(QPen(Qt.GlobalColor.darkGray, 2))
            circle.setBrush(QColor(180, 180, 180))

            letter_item = QGraphicsTextItem(self.key, self)
            font = letter_item.font()
            font.setPointSize(10)
            font.setBold(True)
            letter_item.setFont(font)
            letter_item.setDefaultTextColor(Qt.GlobalColor.darkGray)

            text_item = QGraphicsTextItem(self.block.text, self)
            font2 = text_item.font()
            font2.setPointSize(10)
            font2.setBold(True)
            text_item.setFont(font2)
            text_item.setDefaultTextColor(Qt.GlobalColor.darkGray)

            self.content_items.append((circle, letter_item, text_item, pos))

    # -------------------------
    # Mise à jour géométrie
    # -------------------------
    def _update_geometry(self):
        self.setPos(self.block.x, self.block.y)
        self.rect_item.rect = QRectF(0, 0, self.block.w, self.block.h)
        self.rect_item.update()
        padding = 8
        for circle, letter_item, text_item, pos in self.content_items:
            circle_x = 10
            if pos == "top":
                circle_y = padding
            else:  # "bottom"
                circle_y = self.block.h - self.circle_diameter - padding

            circle.setRect(
                circle_x,
                circle_y,
                self.circle_diameter,
                self.circle_diameter
            )

            # Centrage lettre
            letter_width = letter_item.boundingRect().width()
            letter_height = letter_item.boundingRect().height()
            letter_item.setPos(
                circle_x + (self.circle_diameter - letter_width) / 2,
                circle_y + (self.circle_diameter - letter_height) / 2
            )

            # Le texte doit être aligné verticalement au centre du cercle
            text_item.setPos(
                circle_x + self.circle_diameter + 8,
                circle_y + (self.circle_diameter - text_item.boundingRect().height()) / 2
            )

    # -------------------------
    # Resize public
    # -------------------------
    def resize_block(self, block):
        self.prepareGeometryChange()
        self.block = block
        self._update_geometry()

    # -------------------------
    # Expose animation
    # -------------------------
    def animate_highlight(self):
        self.rect_item.animate_highlight()

    def animate_unhighlight(self):
        self.rect_item.animate_unhighlight()

  
class CanvasView(QGraphicsView):

    def __init__(self):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)
        self._init_scene()
        self._init_view_config()
        self.action_for_states = None
        self._layout_items = {}
        self.controller = None
        self.current_highlight = None
        self.zones = {}
       
            
        
    # Signal unique pour resize centralisé
    resizeSceneRequested = pyqtSignal(int, int)
    

    # =========================
    # 1️⃣ SIGNAUX PUBLICS
    # =========================

    stateDropped = pyqtSignal(str, str, QPointF)
    canvasClicked = pyqtSignal(QPointF)
    itemClicked = pyqtSignal(object)
    mouseMoved = pyqtSignal(QPointF)


    def accept_drop_from_palette(self):
        return True
    # =========================
    # 2️⃣ INITIALISATION
    # =========================


    def set_states_interactive(self, enabled: bool):
        """Active ou désactive le déplacement/redimensionnement des Etats et l'affichage du handle."""
        self._states_interactive = enabled
        for item in self.scene.items():
            if isinstance(item, EtatGraphicsObject):
                item.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsMovable, enabled)
                item.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable, enabled)
                item.set_handle_visible(enabled)
        


    def apply_states_interactive(self):
        """Réapplique l'état interactif courant à tous les Etats (utile après un redraw)."""
        enabled = getattr(self, '_states_interactive', False)
        for item in self.scene.items():
            if isinstance(item, EtatGraphicsObject):
                item.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsMovable, enabled)
                item.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable, enabled)
                item.set_handle_visible(enabled)

    def _init_scene(self):
        
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        # Fixer la taille initiale de la scène à celle du viewport
        self._sync_scene_size()

    def _sync_scene_size(self):
        w = self.viewport().width()
        h = self.viewport().height()
        self.scene.setSceneRect(0, 0, w, h)

    def _init_view_config(self):
        pass

    def handle_state_drop(self, code, label, global_pos):
        scene_pos = self.mapToScene(self.mapFromGlobal(global_pos))
        print(f"Handling state drop in CanvasView: code={code}, label={label}, global_pos={global_pos}, scene_pos={scene_pos}")
        # Bloc ajouté uniquement par StatesController.on_state_dropped (taille adaptée)
        
    # =====================================
    # Resize automatique
    # =====================================
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_scene_size()
        w = self.viewport().width()
        h = self.viewport().height()
        self.resizeSceneRequested.emit(w, h)
            
    # =========================
    # 3️⃣ ÉVÉNEMENTS QT (ÉMISSION)
    # =========================

    def mousePressEvent(self, event):
        pos = self.mapToScene(event.pos())
        self.canvasClicked.emit(pos)
        super().mousePressEvent(event)

    # =========================
    # 4️⃣ MÉTHODES DE RENDU
    # =========================

    def add_zone(self, zone_id, rect):
        pass

    def add_state_graphic(self, state_id, pos):
        pass

    def add_transition_graphic(self, start_id, end_id):
        pass

    def highlight_zone(self, letter: str):
        # Désactiver l’ancien highlight
        # print(f"Highlight zone {letter} self.zones {self.zones}")
        if self.current_highlight in self.zones:
            self.zones[self.current_highlight].animate_unhighlight()

        self.current_highlight = letter

        # Activer le nouveau highlight
        if letter in self.zones:
            self.zones[letter].animate_highlight()

    def clear(self):
        self.scene.clear()

    # =====================================================
    # Construction des blocs
    # =====================================================
    def draw_layout_blocks(self, layout_data):

        # ---- Première création ----
        if not self._layout_items:
            for key, block in layout_data.items():
                item = LayoutBlockGraphicsObject(key, block)
                self.scene.addItem(item)
                self._layout_items[key] = item
                self.zones[key] = item
            return
        
        # ---- Supprimer blocs disparus ----
        for key in list(self._layout_items.keys()):
            if key not in layout_data:
                self.scene.removeItem(self._layout_items[key])
                del self._layout_items[key]
                if key in self.zones:
                    del self.zones[key]

        # ---- Mise à jour blocs existants ----
        for key, block in layout_data.items():
            if key in self._layout_items:
                self._layout_items[key].resize_block(block)
            else:
                item = LayoutBlockGraphicsObject(key, block)
                self.scene.addItem(item)
                self._layout_items[key] = item
                self.zones[key] = item    
                
    # =====================================================
    # Construction des Etats
    # =====================================================
    def draw_state_blocks(self, states):
        for state in states:
            graphics_item = StateGraphicsItem(state)
            self.scene.addItem(graphics_item)

    def remove_all_state_blocks(self):
        for item in list(self.scene.items()):
            if isinstance(item, EtatGraphicsObject):
                self.scene.removeItem(item)
