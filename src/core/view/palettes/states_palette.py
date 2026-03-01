from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QPoint,
    QEvent,
    QPropertyAnimation,
    QEasingCurve,
    QPointF
)

from PyQt6.QtGui import (
    QColor,
    QBrush,
    QPainter,
    QPixmap,
    QPen,
    QCursor, QFont
)

from PyQt6.QtWidgets import (
    QWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QGraphicsDropShadowEffect
)


# ==========================================================
# StatesListWidget (Drag Source Wayland Safe)
# ==========================================================

class StatesListWidget(QListWidget):

    # 🔥 Signal MVC : code, label, position globale
    stateDropped = pyqtSignal(str, str, QPointF)

    def __init__(self, parent=None):
        super().__init__(parent)

        # IMPORTANT : on désactive le drag interne Qt
        self.setDragEnabled(False)
        self.setMouseTracking(True)

        self.drag_label = None
        self.drag_item = None
        self.start_pos = None

    # ------------------------------------------------------
    # Mouse Press
    # ------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if item:
                self.start_pos = event.pos()
                self.drag_item = item
                # Correction : offset dynamique curseur → coin supérieur gauche de l'item
                item_rect = self.visualItemRect(item)
                self.drag_offset = event.pos() - item_rect.topLeft()
        super().mousePressEvent(event)

    # ------------------------------------------------------
    # Mouse Move
    # ------------------------------------------------------
    def mouseMoveEvent(self, event):

        if not self.drag_item:
            return super().mouseMoveEvent(event)

        # seuil anti micro-mouvements
        if (event.pos() - self.start_pos).manhattanLength() < 8:
            return super().mouseMoveEvent(event)
        #print(f"MouseMove: pos={event.pos()}, start={self.start_pos}, offset={self.drag_offset}")
        if not self.drag_label:
            self._create_drag_sprite()

        global_pos = self.mapToGlobal(event.pos())
        self.drag_label.move(global_pos) # Pas de self.drag_offset)

    # ------------------------------------------------------
    # Mouse Release
    # ------------------------------------------------------
    def mouseReleaseEvent(self, event):

        if not self.drag_label:
            return super().mouseReleaseEvent(event)

        global_pos = QCursor.pos()
        widget = self.window().childAt(
            self.window().mapFromGlobal(global_pos)
        )

        # Recherche directe du CanvasView dans la fenêtre
        from core.view.canvas_view import CanvasView
        canvas = self.window().findChild(CanvasView)
        if canvas:
            # Vérifie que le curseur est bien au-dessus du canvas
            canvas_rect = canvas.rect()
            canvas_pos = canvas.mapToGlobal(canvas_rect.topLeft())
            canvas_rect_global = canvas_rect.translated(canvas_pos)
            if canvas_rect_global.contains(global_pos + QPoint(50, 0)):
                code = self.drag_item.data(Qt.ItemDataRole.UserRole)
                label = self.drag_item.toolTip()
                # Conversion de la position globale en position scène
                scene_pos = canvas.mapToScene(canvas.mapFromGlobal(global_pos))
                # print(f"MouseRelease: code={code}, label={label}, scene_pos=({scene_pos.x()}, {scene_pos.y()})")
                self.stateDropped.emit(code, label, scene_pos)
                self._cleanup_drag()
                return
        self._animate_return()

        super().mouseReleaseEvent(event)

    # ------------------------------------------------------
    # Sprite creation
    # ------------------------------------------------------
    def _create_drag_sprite(self):
        
        width, height, roundness = 50, 30, 2
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        #painter.begin(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setBrush(QBrush(QColor(255, 255, 180)))
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawRoundedRect(0, 0, width, height, roundness, roundness)

        code = str(self.drag_item.data(Qt.ItemDataRole.UserRole))
        label = self.drag_item.toolTip()

        painter.setPen(Qt.GlobalColor.black)
        painter.setFont(QFont("Arial", 12, QFont.Weight.Normal ))
        painter.drawText( 12 , height // 2 + 6, code)
        #painter.drawText(20, 75, label)
        painter.end()

        self.drag_label = QLabel(self.window())
        self.drag_label.setPixmap(pixmap)
        self.drag_label.setFixedSize(width, height)
        self.drag_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        self.drag_label.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
        )

        # Ombre portée
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setOffset(4, 4)
        self.drag_label.setGraphicsEffect(shadow)

        self.drag_label.show()
        
    # ------------------------------------------------------
    # Animation retour si drop invalide
    # ------------------------------------------------------
    def _animate_return(self):

        anim = QPropertyAnimation(self.drag_label, b"pos")
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        current = self.drag_label.pos()
        origin = self.mapToGlobal(self.start_pos) - self.drag_offset

        anim.setStartValue(current)
        anim.setEndValue(origin)

        anim.finished.connect(self._cleanup_drag)
        anim.start()

        # éviter garbage collection
        self._anim = anim

    # ------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------
    def _cleanup_drag(self):
        if self.drag_label:
            self.drag_label.deleteLater()

        self.drag_label = None
        self.drag_item = None
        self.start_pos = None


# ==========================================================
# StatesPalette (Vue MVC)
# ==========================================================

class StatesPalette(QWidget):

    # 🔥 Signaux MVC
    resetRequested = pyqtSignal()
    loadRequested = pyqtSignal()
    saveRequested = pyqtSignal()

    # 🔥 Relais du drop vers l'extérieur
    stateDropped = pyqtSignal(str, str, QPointF)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    # ------------------------------------------------------
    # UI
    # ------------------------------------------------------
    def _setup_ui(self):

        layout = QVBoxLayout(self)

        title = QLabel("Etats")
        layout.addWidget(title)

        self.states_list = StatesListWidget()
        layout.addWidget(self.states_list)

        self.btn_reinit = QPushButton("Réinitialiser")
        self.btn_charger = QPushButton("Ouvrir")
        self.btn_sauvegarder = QPushButton("Enregistrer")

        layout.addWidget(self.btn_reinit)
        layout.addWidget(self.btn_charger)
        layout.addWidget(self.btn_sauvegarder)
        layout.addStretch()

        # Connexions MVC
        self.btn_reinit.clicked.connect(self.resetRequested.emit)
        self.btn_charger.clicked.connect(self.loadRequested.emit)
        self.btn_sauvegarder.clicked.connect(self.saveRequested.emit)

        # Relais du drop avec conversion QPoint → QPointF
        def traced_emit_state_dropped(code, label, global_pos):
            from PyQt6.QtCore import QPointF
            # Conversion si nécessaire
            if isinstance(global_pos, QPointF):
                self.stateDropped.emit(code, label, global_pos)
            else:
                self.stateDropped.emit(code, label, QPointF(global_pos))
        self.states_list.stateDropped.connect(traced_emit_state_dropped)

        # Hover reset
        self.states_list.viewport().installEventFilter(self)

    # ------------------------------------------------------
    # Remplissage liste
    # ------------------------------------------------------
    def fill_etat_list(self, etats):

        self.states_list.clear()

        for etat in reversed(etats):
            item = QListWidgetItem(f"{etat.code} - {etat.label}")
            item.setData(Qt.ItemDataRole.UserRole, etat.code)
            item.setToolTip(etat.label)

            # Style initial
            item.setBackground(QBrush(Qt.GlobalColor.black))
            item.setForeground(QBrush(Qt.GlobalColor.white))

            self.states_list.addItem(item)

    # ------------------------------------------------------
    # Suppression état
    # ------------------------------------------------------
    def remove_state_item(self, code):

        for i in range(self.states_list.count()):
            item = self.states_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == code:
                self.states_list.takeItem(i)
                break

    # ------------------------------------------------------
    # Hover gestion
    # ------------------------------------------------------
    def eventFilter(self, obj, event):

        if obj == self.states_list.viewport():
            if event.type() == QEvent.Type.Leave:
                self._reset_list_visuals()

        return super().eventFilter(obj, event)

    def _reset_list_visuals(self):

        for i in range(self.states_list.count()):
            item = self.states_list.item(i)
            item.setBackground(QBrush(Qt.GlobalColor.black))
            item.setForeground(QBrush(Qt.GlobalColor.white))