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
