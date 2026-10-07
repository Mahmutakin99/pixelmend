"""Read macOS pressure and wait between owned model processes, never suspend GPU work."""
import ctypes
import sys
import time

GIB = 1024**3
MIN_AVAILABLE = 256 * 1024**2
MIN_SWAP_DISK = 512 * 1024**2


def memory_pressure():
    if sys.platform != 'darwin':
        return 'unknown'
    try:
        value = ctypes.c_int()
        length = ctypes.c_size_t(ctypes.sizeof(value))
        query = ctypes.CDLL(None).sysctlbyname
        query.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
                          ctypes.c_void_p, ctypes.c_size_t]
        query.restype = ctypes.c_int
        if query(b'kern.memorystatus_vm_pressure_level', ctypes.byref(value),
                 ctypes.byref(length), None, 0):
            return 'unknown'
        # This sysctl exports dispatch flags, rather than XNU's internal enum.
        return {1: 'normal', 2: 'warning', 4: 'critical'}.get(value.value, 'unknown')
    except (OSError, AttributeError):
        return 'unknown'


def should_wait(host, minimum_available=MIN_AVAILABLE):
    return (host.get('memory_pressure') == 'critical'
            or host['available_memory_bytes'] < minimum_available
            or host.get('swap_disk_free_bytes', GIB) < MIN_SWAP_DISK)


class MemoryGate:
    def __init__(self, resources, *, clock=time.monotonic, wait=None):
        self.resources = resources
        self.clock = clock
        self.sleep = wait

    def wait(self, cancel, on_event, *, minimum_available=MIN_AVAILABLE, force_recovery=False, deadline=None):
        recovering = False
        stable_since = None
        while True:
            if deadline is not None and self.clock() >= deadline:
                from .generative_process import RuntimeErrorCode
                raise RuntimeErrorCode('timeout')
            if cancel.is_set():
                raise InterruptedError()
            blocked = should_wait(self.resources(), minimum_available)
            if not blocked and not recovering and not force_recovery:
                return
            if not recovering:
                on_event({'event': 'stage', 'stage': 'waiting_for_memory'})
                recovering = True
            if blocked:
                stable_since = None
            elif stable_since is None:
                stable_since = self.clock()
            elif self.clock() - stable_since >= 10:
                return
            interval=2 if deadline is None else min(2,max(0,deadline-self.clock()))
            if (self.sleep or cancel.wait)(interval):
                raise InterruptedError()
