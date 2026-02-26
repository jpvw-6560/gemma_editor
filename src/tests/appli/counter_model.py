class CounterModel:
    """Logique métier : gère la donnée."""
    def __init__(self):
        self._value = 0

    def increment(self):
        self._value += 1
        return self._value

    def get_value(self):
        return self._value
