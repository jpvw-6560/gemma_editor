class ModeManager:

    def __init__(self, canvas, right_menu):
        self.canvas = canvas
        self.right_menu = right_menu
        self.current_controller = None
        self.canvas_controller = None
        self.layout_controller = None
        self.states_controller = None

    def activate(self, mode_name: str):

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
        # (Ré)instanciation du CanvasController à chaque changement de mode
        from core.controller.canvas_controller import CanvasController
        self.canvas_controller = CanvasController(
            self.canvas,
            self.layout_controller,
            self.states_controller
        )