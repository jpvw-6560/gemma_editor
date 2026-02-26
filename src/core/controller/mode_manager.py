class ModeManager:

    def __init__(self,  canvas):
        self.canvas = canvas
        self.current_controller = None

    def activate(self, mode_name):

        if self.current_controller:
            self.current_controller.disconnect()

        if mode_name == "layout":
            from core.controller.layout_controller import LayoutController
            self.current_controller = LayoutController( self.canvas)
        """
        elif mode_name == "states":
            from core.controller.states_controller import StatesController
            self.current_controller = StatesController(self.model, self.canvas)

        elif mode_name == "transitions":
            from core.controller.transitions_controller import TransitionsController
            self.current_controller = TransitionsController(self.model, self.canvas)
        """
        self.current_controller.connect()