"""One native compute slot, with queued user jobs ahead of background probes."""
from contextlib import contextmanager
import threading


class _JobTicket:
    def __init__(self, coordinator):
        self.coordinator=coordinator;self.released=False

    def release(self):
        with self.coordinator._condition:
            if not self.released:
                self.released=True;self.coordinator._pending_jobs-=1
                self.coordinator._condition.notify_all()


class ComputeCoordinator:
    def __init__(self):
        self._condition=threading.Condition();self._active=False;self._pending_jobs=0

    @property
    def pending_jobs(self):
        with self._condition:return self._pending_jobs

    def reserve_job(self):
        with self._condition:
            self._pending_jobs+=1
            return _JobTicket(self)

    @contextmanager
    def operation(self,kind,cancel=None):
        if kind not in {'job','probe'}:raise ValueError('invalid compute kind')
        with self._condition:
            while self._active or kind=='probe' and self._pending_jobs:
                if cancel is not None and cancel.is_set():raise InterruptedError()
                self._condition.wait(.05)
            if cancel is not None and cancel.is_set():raise InterruptedError()
            self._active=True
        try:yield
        finally:
            with self._condition:
                self._active=False;self._condition.notify_all()
