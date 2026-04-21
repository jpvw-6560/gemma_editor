class ModeManager:

    def __init__(self, canvas, right_menu):
        self.canvas = canvas
        self.right_menu = right_menu
        self.current_controller = None
        self.canvas_controller = None
        self.layout_controller = None
        self.states_controller = None
        self.transitions_controller = None

    def activate(self, mode_name: str):

        # Déconnecter l'ancien CanvasController avant de le remplacer
        # (évite l'accumulation de connexions à resizeSceneRequested)
        if self.canvas_controller is not None:
            try:
                self.canvas.resizeSceneRequested.disconnect(
                    self.canvas_controller.on_resize_scene
                )
            except (TypeError, RuntimeError):
                pass

        # Vider la sélection courante pour purger les poignées (SegmentHandle/AttachHandle)
        # qui sont des QGraphicsObject avec méthodes virtuelles overridées en Python.
        # Si leur flèche parente perd sa référence Python pendant un changement de mode,
        # un appel de paint()/boundingRect() C++ sans vtable Python = "pure virtual method called".
        try:
            self.canvas.scene.clearSelection()
        except (RuntimeError, AttributeError):
            pass

        # Nettoyage éventuel
        #if self.current_controller:
        #    self.current_controller.cleanup()

        if mode_name == "layout":
            from core.controller.layout_controller import LayoutController
            from core.view.palettes.layout_palette import LayoutPalette
            palette = LayoutPalette()
            self.layout_controller = LayoutController(self.canvas, palette)
            self.right_menu.set_palette_widget(palette)
            self.current_controller = self.layout_controller
            # Désactiver l'interactivité des états
            self.canvas.set_states_interactive(False)
            self.canvas.action_for_states = False
        elif mode_name == "states":
            from core.controller.states_controller import StatesController
            from core.view.palettes.states_palette import StatesPalette
            palette = StatesPalette()
            
            # Relais du signal drop palette → canvas
            from PyQt6.QtCore import QPointF
            def relay_state_dropped(code, label, pos):
                # Conversion QPoint (palette) → QPointF (canvas)
                if isinstance(pos, QPointF):
                    self.canvas.stateDropped.emit(code, label, pos)
                else:
                    self.canvas.stateDropped.emit(code, label, QPointF(pos))
            palette.stateDropped.connect(relay_state_dropped)
            self.states_controller = StatesController(self.canvas, palette)
            self.right_menu.set_palette_widget(palette)
            self.current_controller = self.states_controller
            self.current_controller.connect()
            # Activer l'interactivité des états
            self.canvas.set_states_interactive(True)
            self.canvas.action_for_states = True
        elif mode_name == "transitions":
            from core.controller.transitions_controller import TransitionsController
            from core.view.palettes.transitions_palette import TransitionsPalette
            palette = TransitionsPalette()
            # Relais du signal drop palette → canvas (si nécessaire)
            # Exemple : palette.transitionDropped.connect(...)
            self.transitions_controller = TransitionsController(self.canvas, palette)
            self.right_menu.set_palette_widget(palette)
            self.current_controller = self.transitions_controller
            if hasattr(self.current_controller, "connect"):
                self.current_controller.connect()
            # Désactiver l'interactivité des états
            self.canvas.set_states_interactive(False)
            self.canvas.action_for_states = False
            print("Transitions mode activated")
        # (Ré)instanciation du CanvasController à chaque changement de mode
        from core.controller.canvas_controller import CanvasController
        self.canvas_controller = CanvasController(
            self.canvas,
            self.layout_controller,
            self.states_controller
        )