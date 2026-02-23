class EventBus:
    def __init__(self):
        self._listeners = {}

    def subscribe(self, event_name, callback):
        self._listeners.setdefault(event_name, []).append(callback)

    def emit(self, event_name, data=None):
        for callback in self._listeners.get(event_name, []):
            callback(data)