from gemma.domain.entities.project import Project
from gemma.application.event_bus import EventBus
from gemma.application.command_stack import CommandStack
from gemma.application.use_cases.add_state_use_case import AddStateUseCase

class Container:
    def __init__(self):
        self.project = Project()
        self.event_bus = EventBus()
        self.command_stack = CommandStack()
        self.add_state_use_case = AddStateUseCase(
            self.project,
            self.event_bus,
            self.command_stack
        )