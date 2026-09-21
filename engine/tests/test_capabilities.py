from types import SimpleNamespace


def test_capabilities_keep_unmeasured_accelerator_memory_unknown(monkeypatch) -> None:
    """Inventing a GPU budget from host RAM would admit unsupported models."""
    import pixelmend_engine.capabilities as capabilities

    monkeypatch.setattr(
        capabilities.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(total=16_000, available=6_000),
    )
    monkeypatch.setattr(capabilities.os, "cpu_count", lambda: 10)
    monkeypatch.setattr(capabilities, "available_execution_providers", lambda: ("CPUExecutionProvider",))

    report = capabilities.collect_capabilities()

    assert report.host_ram_total_bytes == 16_000
    assert report.host_ram_available_bytes == 6_000
    assert report.cpu_count == 10
    assert report.execution_providers == ("CPUExecutionProvider",)
    assert report.accelerator.memory_kind == "unknown"
    assert report.accelerator.device_budget_bytes is None


def test_capabilities_report_apple_device_and_unified_memory_without_inventing_vram(monkeypatch) -> None:
    import pixelmend_engine.capabilities as capabilities

    monkeypatch.setattr(capabilities.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(capabilities, "_mac_sysctl", lambda key: {"hw.model": "Mac16,1", "machdep.cpu.brand_string": "Apple M4"}.get(key))
    monkeypatch.setattr(capabilities.psutil, "virtual_memory", lambda: SimpleNamespace(total=16_000, available=6_000))
    monkeypatch.setattr(capabilities, "available_execution_providers", lambda: ("CoreMLExecutionProvider", "CPUExecutionProvider"))

    report = capabilities.collect_capabilities()

    assert report.accelerator.identity == "Apple M4 (Mac16,1)"
    assert report.accelerator.memory_kind == "unified"
    assert report.accelerator.device_budget_bytes is None
