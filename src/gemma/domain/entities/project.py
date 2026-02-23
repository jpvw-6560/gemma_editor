class Project:
    def __init__(self):
        self.states = []

    def add_state(self, state):
        self.states.append(state)
        return state