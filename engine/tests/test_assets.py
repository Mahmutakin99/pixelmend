from io import BytesIO

import numpy as np
import pytest
from PIL import Image


def _png_bytes() -> BytesIO:
    image = Image.fromarray(
        np.array([[[10, 20, 30, 128], [40, 50, 60, 255]]], dtype=np.uint8)
    )
    encoded = BytesIO()
    image.save(encoded, format="PNG")
    encoded.seek(0)
    return encoded


def test_import_keeps_only_an_opaque_id_and_normalized_preview() -> None:
    """Changing the source filename must never change the returned asset identity."""
    from pixelmend_engine.assets import AssetStore

    store = AssetStore()

    imported = store.import_image(_png_bytes())

    assert imported.asset_id
    assert "/" not in imported.asset_id
    assert imported.width == 2
    assert imported.height == 1
    with Image.open(BytesIO(store.preview_bytes(imported.asset_id))) as preview:
        assert preview.mode == "RGBA"
        np.testing.assert_array_equal(
            np.asarray(preview),
            np.array([[[10, 20, 30, 128], [40, 50, 60, 255]]], dtype=np.uint8),
        )


def test_delete_rejects_an_asset_while_a_job_reference_is_active() -> None:
    """Dropping a source used by a job would make the job non-reproducible."""
    from pixelmend_engine.assets import AssetInUseError, AssetStore

    store = AssetStore()
    imported = store.import_image(_png_bytes())
    store.acquire_for_job(imported.asset_id)

    with pytest.raises(AssetInUseError):
        store.delete(imported.asset_id)

    store.release_from_job(imported.asset_id)
    store.delete(imported.asset_id)
    assert not store.contains(imported.asset_id)


def test_asset_budget_rejects_import_without_losing_existing_source():
    from pixelmend_engine.assets import AssetStore, AssetCapacityError

    store = AssetStore(max_assets=1)
    first = store.import_image(_png_bytes())
    with pytest.raises(AssetCapacityError):
        store.import_image(_png_bytes())
    assert store.contains(first.asset_id)
    store.delete(first.asset_id)
    assert store.import_image(_png_bytes()).width == 2


def test_expiry_retains_pinned_source_and_close_releases_all():
    from pixelmend_engine.assets import AssetStore

    store = AssetStore(ttl_seconds=0)
    first = store.import_image(_png_bytes())
    store.acquire_for_job(first.asset_id)
    store.expire()
    assert store.contains(first.asset_id)
    store.release_from_job(first.asset_id)
    store.expire()
    assert not store.contains(first.asset_id)
    store.import_image(_png_bytes())
    store.close()
    assert store.used_bytes == 0
