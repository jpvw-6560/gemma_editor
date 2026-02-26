class BaseModeController:

    def __init__(self, canvas):
        self.canvas = canvas

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError