from gemma.application.commands.add_state_command import AddStateCommand

class AddStateUseCase:
    def __init__(self, project, event_bus, command_stack):
        self.project = project
        self.event_bus = event_bus
        self.command_stack = command_stack

    def execute(self, name, x, y):
        cmd = AddStateCommand(self.project, name, x, y)
        self.command_stack.execute(cmd)
        self.event_bus.emit("STATE_ADDED", cmd.state)