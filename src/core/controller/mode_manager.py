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
        elif mode_name == "states":
            from core.controller.states_controller import StatesController
            from core.view.palettes.states_palette import StatesPalette
            palette = StatesPalette()
            self.states_controller = StatesController(self.canvas, palette)
            self.right_menu.set_palette_widget(palette)
            self.current_controller = self.states_controller
            self.current_controller.connect()
        # (Ré)instanciation du CanvasController à chaque changement de mode
        from core.controller.canvas_controller import CanvasController
        self.canvas_controller = CanvasController(
            self.canvas,
            self.layout_controller,
            self.states_controller
        )