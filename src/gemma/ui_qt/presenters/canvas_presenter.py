from PyQt6.QtWidgets import QGraphicsEllipseItem

class CanvasPresenter:
    def __init__(self, scene, event_bus):
        self.scene = scene
        event_bus.subscribe("STATE_ADDED", self.on_state_added)

    def on_state_added(self, state):
        item = QGraphicsEllipseItem(state.x, state.y, 60, 60)
        self.scene.addItem(item)