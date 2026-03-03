from PyQt6.QtCore import QObject

class CanvasController(QObject):
    """
    Contrôleur central pour gérer les signaux de resize du canvas et déléguer
    aux contrôleurs de layout et d'états.
    """
    def __init__(self, canvas, layout_controller, states_controller):
        super().__init__()
        self.canvas = canvas
        self.layout_controller = layout_controller
        self.states_controller = states_controller

        # Connexion du signal unique (à créer dans CanvasView)
        self.canvas.resizeSceneRequested.connect(self.on_resize_scene)

    def on_resize_scene(self, w, h):
        
        if self.states_controller:
            self.states_controller.on_resize_states(w, h)
            print(f"    CanvasController: 1 ==> states_controller")
        if self.layout_controller:
            self.layout_controller.on_resize_layout(w, h)
            print(f"    CanvasController: 2 ==> layout_controller")