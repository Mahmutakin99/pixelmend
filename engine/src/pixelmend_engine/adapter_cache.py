"""Small lifetime-owned cache for expensive ONNX model sessions."""

from collections import OrderedDict
from threading import Lock


class AdapterCache:
    """Reuse sessions in PixelMend's single inference worker without sharing jobs."""

    def __init__(self, max_entries=2):
        if max_entries < 1:
            raise ValueError('max_entries must be positive')
        self.max_entries = max_entries
        self._items = OrderedDict()
        self._lock = Lock()

    def get(self, key, factory):
        with self._lock:
            value = self._items.pop(key, None)
            if value is not None:
                self._items[key] = value
                return value
            # Release the oldest native session before the next allocation.
            # Loading first can briefly double peak memory for large models.
            while len(self._items) >= self.max_entries:
                _, stale = self._items.popitem(last=False)
                close = getattr(stale, 'close', None)
                if close:
                    close()
            value = factory()
            self._items[key] = value
            return value

    def close(self):
        with self._lock:
            values = list(self._items.values())
            self._items.clear()
        for value in values:
            close = getattr(value, 'close', None)
            if close:
                close()
