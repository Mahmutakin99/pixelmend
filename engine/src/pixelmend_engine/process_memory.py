"""Darwin's process physical-footprint counter; unavailable stays unknown.

The structure matches RUSAGE_INFO_V2 in the Apple SDK sys/resource.h.
Keep this metric separate from RSS and MLX allocation; do not add them.
"""
import ctypes
import sys


class RUsageV2(ctypes.Structure):
    _fields_ = [('ri_uuid', ctypes.c_uint8 * 16)] + [
        (name, ctypes.c_uint64) for name in (
            'ri_user_time', 'ri_system_time', 'ri_pkg_idle_wkups',
            'ri_interrupt_wkups', 'ri_pageins', 'ri_wired_size',
            'ri_resident_size', 'ri_phys_footprint', 'ri_proc_start_abstime',
            'ri_proc_exit_abstime', 'ri_child_user_time', 'ri_child_system_time',
            'ri_child_pkg_idle_wkups', 'ri_child_interrupt_wkups',
            'ri_child_pageins', 'ri_child_elapsed_abstime',
            'ri_diskio_bytesread', 'ri_diskio_byteswritten',
        )
    ]


class MacFootprint:
    def __init__(self, *, platform_name=None, query=None):
        self.query = None
        if (platform_name or sys.platform) != 'darwin':
            return
        if query is not None:
            self.query = query
            return
        try:
            library = ctypes.CDLL('/usr/lib/libproc.dylib')
            self.query = library.proc_pid_rusage
            self.query.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
            self.query.restype = ctypes.c_int
        except (OSError, AttributeError):
            pass

    def read(self, pid):
        if self.query is None:
            return None
        usage = RUsageV2()
        if self.query(pid, 2, ctypes.byref(usage)) != 0:
            return None
        return usage.ri_phys_footprint or None
