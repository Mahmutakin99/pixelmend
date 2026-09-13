"""Report observed host and inference backend capabilities without guesses."""

import os
from dataclasses import asdict, dataclass

import psutil


@dataclass(frozen=True, slots=True)
class AcceleratorCapabilities:
    """Describe only accelerator facts the sidecar can actually measure."""

    identity: str | None
    memory_kind: str
    device_budget_bytes: int | None
    device_headroom_bytes: int | None


@dataclass(frozen=True, slots=True)
class Capabilities:
    """Carry host capacity separately from provider availability and probes."""

    host_ram_total_bytes: int
    host_ram_available_bytes: int
    cpu_count: int | None
    accelerator: AcceleratorCapabilities
    execution_providers: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        """Convert immutable capability facts to JSON-ready primitive values."""
        return asdict(self)


def available_execution_providers() -> tuple[str, ...]:
    """Read ORT build providers when installed; this is not a model session probe."""
    try:
        import onnxruntime
    except ImportError:
        return ()
    return tuple(onnxruntime.get_available_providers())


def collect_capabilities() -> Capabilities:
    """Collect measurable host facts and preserve unavailable accelerator data."""
    memory = psutil.virtual_memory()
    return Capabilities(
        host_ram_total_bytes=int(memory.total),
        host_ram_available_bytes=int(memory.available),
        cpu_count=os.cpu_count(),
        accelerator=AcceleratorCapabilities(
            identity=None,
            memory_kind="unknown",
            device_budget_bytes=None,
            device_headroom_bytes=None,
        ),
        execution_providers=available_execution_providers(),
    )
