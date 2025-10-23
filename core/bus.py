class MessageBus:
    def __init__(self):
        self._subscribers = {}

    def subscribe(self, topic, fn):
        self._subscribers.setdefault(topic, []).append(fn)

    def publish(self, topic, payload):
        for fn in self._subscribers.get(topic, []):
            fn(payload)
