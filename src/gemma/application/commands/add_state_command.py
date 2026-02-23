from .command import Command
from gemma.domain.entities.state import State

class AddStateCommand(Command):
    def __init__(self, project, name, x, y):
        self.project = project
        self.name = name
        self.x = x
        self.y = y
        self.state = None

    def execute(self):
        self.state = State(self.name, self.x, self.y)
        self.project.add_state(self.state)

    def undo(self):
        self.project.states.remove(self.state)