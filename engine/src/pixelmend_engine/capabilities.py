"""Report observed host and inference backend capabilities without guesses."""

import os
import platform
import subprocess
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


def generative_capabilities(total_ram_bytes: int, runtime_installed: bool) -> dict:
    """Eligibility facts only; accepted profiles require separate hardware/quality evidence."""
    try:
        major = int(platform.mac_ver()[0].split('.')[0])
    except ValueError:
        major = 0
    return {'platform_supported': platform.system() == 'Darwin' and platform.machine() == 'arm64'
            and major >= 15 and total_ram_bytes >= 16*1024**3,
            'runtime_installed': runtime_installed, 'minimum_ram_bytes': 16*1024**3,
            'minimum_macos_major': 15, 'runtime': 'mlx', 'translation_runtime': 'torch-cpu',
            'accepted_profiles': []}


def _mac_sysctl(key: str) -> str | None:
    """Read a small, public macOS hardware fact without treating it as VRAM."""
    try:
        value = subprocess.run(['sysctl', '-n', key], check=True, capture_output=True,
                               text=True, timeout=1).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return value or None


def collect_capabilities() -> Capabilities:
    """Collect measurable host facts and preserve unavailable accelerator data."""
    memory = psutil.virtual_memory()
    is_macos = platform.system() == 'Darwin'
    machine = _mac_sysctl('hw.model') if is_macos else None
    chip = _mac_sysctl('machdep.cpu.brand_string') if is_macos else None
    identity = f'{chip} ({machine})' if chip and machine else chip or machine
    return Capabilities(
        host_ram_total_bytes=int(memory.total),
        host_ram_available_bytes=int(memory.available),
        cpu_count=os.cpu_count(),
        accelerator=AcceleratorCapabilities(
            identity=identity,
            # Apple Silicon memory is shared. Its available amount is not a GPU-only
            # allocation limit, so the budget remains intentionally unmeasured.
            memory_kind="unified" if identity and is_macos else "unknown",
            device_budget_bytes=None,
            device_headroom_bytes=None,
        ),
        execution_providers=available_execution_providers(),
    )
