import struct
import zlib
from io import BytesIO

import numpy as np
import pytest
from PIL import Image, ImageCms


def _encoded_image(
    image: Image.Image,
    image_format: str,
    **save_options: object,
) -> BytesIO:
    encoded = BytesIO()
    image.save(encoded, format=image_format, **save_options)
    encoded.seek(0)
    return encoded


def _encoded_16_bit_rgb_png(values: list[int]) -> BytesIO:
    def chunk(name: bytes, payload: bytes) -> bytes:
        checksum = zlib.crc32(name + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + name + payload + struct.pack(">I", checksum)

    pixels = b"".join(struct.pack(">HHH", value, value, value) for value in values)
    header = struct.pack(">IIBBBBB", len(values), 1, 16, 2, 0, 0, 0)
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"\x00" + pixels))
        + chunk(b"IEND", b"")
    )
    return BytesIO(payload)


@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WEBP", "TIFF"])
def test_load_image_normalizes_supported_formats(image_format: str) -> None:
    from pixelmend_engine.imageio import load_image

    source = _encoded_image(Image.new("RGB", (3, 2), (10, 20, 30)), image_format)

    asset = load_image(source)

    assert asset.rgb.shape == (2, 3, 3)
    assert asset.rgb.dtype == np.uint8
    assert asset.rgb.flags.c_contiguous
    assert asset.alpha is None
    assert asset.width == 3
    assert asset.height == 2
    assert asset.metadata.source_format == image_format
    assert asset.metadata.source_mode == "RGB"
    assert asset.metadata.source_size == (3, 2)
    assert asset.warnings == ()


def test_load_image_applies_exif_orientation_to_pixels() -> None:
    from pixelmend_engine.imageio import load_image

    pixels = np.array(
        [
            [[255, 0, 0], [0, 255, 0]],
            [[0, 0, 255], [255, 255, 0]],
            [[255, 0, 255], [0, 255, 255]],
        ],
        dtype=np.uint8,
    )
    image = Image.fromarray(pixels)
    exif = Image.Exif()
    exif[274] = 6

    asset = load_image(_encoded_image(image, "PNG", exif=exif))

    np.testing.assert_array_equal(asset.rgb, np.rot90(pixels, k=3))
    assert asset.metadata.source_size == (2, 3)
    assert (asset.width, asset.height) == (3, 2)
    assert asset.metadata.source_exif is not None


def test_load_image_detaches_alpha_and_preview_restores_it() -> None:
    from pixelmend_engine.imageio import encode_preview_png, load_image

    rgba = np.array(
        [
            [[10, 20, 30, 0], [40, 50, 60, 127]],
            [[70, 80, 90, 200], [100, 110, 120, 255]],
        ],
        dtype=np.uint8,
    )

    asset = load_image(_encoded_image(Image.fromarray(rgba), "PNG"))

    np.testing.assert_array_equal(asset.rgb, rgba[:, :, :3])
    np.testing.assert_array_equal(asset.alpha, rgba[:, :, 3])

    with Image.open(BytesIO(encode_preview_png(asset))) as preview:
        np.testing.assert_array_equal(np.asarray(preview), rgba)
        assert preview.format == "PNG"
        assert preview.n_frames == 1
        assert preview.info["icc_profile"] == asset.metadata.srgb_icc_profile
        assert len(preview.getexif()) == 0


def test_load_image_detaches_la_alpha() -> None:
    from pixelmend_engine.imageio import load_image

    la = np.array([[[20, 0], [200, 255]]], dtype=np.uint8)

    asset = load_image(_encoded_image(Image.fromarray(la), "PNG"))

    np.testing.assert_array_equal(
        asset.rgb,
        np.array([[[20, 20, 20], [200, 200, 200]]], dtype=np.uint8),
    )
    np.testing.assert_array_equal(asset.alpha, np.array([[0, 255]], dtype=np.uint8))


def test_load_image_detaches_palette_transparency() -> None:
    from pixelmend_engine.imageio import load_image

    palette_image = Image.new("P", (2, 1))
    palette_image.putpalette([255, 0, 0, 0, 255, 0] + [0] * 762)
    palette_image.putdata([0, 1])

    asset = load_image(
        _encoded_image(palette_image, "PNG", transparency=bytes([0, 255]))
    )

    np.testing.assert_array_equal(
        asset.rgb,
        np.array([[[255, 0, 0], [0, 255, 0]]], dtype=np.uint8),
    )
    np.testing.assert_array_equal(asset.alpha, np.array([[0, 255]], dtype=np.uint8))


def test_load_image_converts_valid_embedded_profile_to_srgb_pixels() -> None:
    from pixelmend_engine.imageio import load_image

    lab_profile = ImageCms.ImageCmsProfile(
        ImageCms.createProfile("LAB")
    ).tobytes()
    source = _encoded_image(
        Image.new("LAB", (1, 1), (128, 128, 128)),
        "TIFF",
        icc_profile=lab_profile,
    )

    asset = load_image(source)

    np.testing.assert_allclose(asset.rgb[0, 0], [119, 119, 119], atol=1)
    assert asset.warnings == ()
    assert asset.metadata.srgb_icc_profile != lab_profile


def test_load_image_warns_and_falls_back_for_invalid_icc() -> None:
    from pixelmend_engine.imageio import ImageWarningCode, load_image

    source = _encoded_image(
        Image.new("RGB", (1, 1), (10, 20, 30)),
        "PNG",
        icc_profile=b"not-an-icc-profile",
    )

    asset = load_image(source)

    np.testing.assert_array_equal(asset.rgb[0, 0], [10, 20, 30])
    assert asset.warnings == (ImageWarningCode.INVALID_ICC_ASSUMED_SRGB,)


def test_load_image_warns_when_converting_cmyk() -> None:
    from pixelmend_engine.imageio import ImageWarningCode, load_image

    source = _encoded_image(Image.new("CMYK", (2, 1), (0, 255, 255, 0)), "JPEG")

    asset = load_image(source)

    assert asset.rgb.shape == (1, 2, 3)
    assert asset.rgb.dtype == np.uint8
    assert asset.warnings == (ImageWarningCode.CMYK_CONVERTED_TO_SRGB,)


def test_load_image_scales_16_bit_integer_pixels_to_uint8() -> None:
    from pixelmend_engine.imageio import ImageWarningCode, load_image

    values = np.array([[0, 32768, 65535]], dtype=np.uint16)
    source = _encoded_image(Image.fromarray(values), "TIFF")

    asset = load_image(source)

    expected = np.array([[[0, 0, 0], [128, 128, 128], [255, 255, 255]]])
    np.testing.assert_array_equal(asset.rgb, expected)
    assert asset.warnings == (ImageWarningCode.BIT_DEPTH_REDUCED_TO_UINT8,)


def test_load_image_warns_when_pillow_reduces_16_bit_rgb_png() -> None:
    from pixelmend_engine.imageio import ImageWarningCode, load_image

    asset = load_image(_encoded_16_bit_rgb_png([0, 32768, 65535]))

    np.testing.assert_array_equal(
        asset.rgb,
        np.array([[[0, 0, 0], [128, 128, 128], [255, 255, 255]]]),
    )
    assert asset.warnings == (ImageWarningCode.BIT_DEPTH_REDUCED_TO_UINT8,)


@pytest.mark.parametrize(
    ("values", "dtype"),
    [([0, 65536], np.int32), ([0.0, 2.0], np.float32)],
)
def test_load_image_rejects_hdr_modes_without_tone_mapping(
    values: list[int] | list[float],
    dtype: np.dtype,
) -> None:
    from pixelmend_engine.imageio import UnsupportedImageModeError, load_image

    image = Image.fromarray(np.asarray([values], dtype=dtype))
    source = _encoded_image(image, "TIFF")

    with pytest.raises(UnsupportedImageModeError):
        load_image(source)


def test_load_image_uses_first_frame_with_warning() -> None:
    from pixelmend_engine.imageio import ImageWarningCode, load_image

    source = BytesIO()
    Image.new("RGB", (2, 1), (255, 0, 0)).save(
        source,
        format="TIFF",
        save_all=True,
        append_images=[Image.new("RGB", (2, 1), (0, 255, 0))],
    )
    source.seek(0)

    asset = load_image(source)

    np.testing.assert_array_equal(asset.rgb, np.array([[[255, 0, 0]] * 2]))
    assert asset.warnings == (ImageWarningCode.MULTIFRAME_FIRST_FRAME_ONLY,)


@pytest.mark.parametrize("image_format", ["GIF", "BMP"])
def test_load_image_rejects_recognizable_unsupported_formats(
    image_format: str,
) -> None:
    from pixelmend_engine.imageio import UnsupportedImageFormatError, load_image

    source = _encoded_image(Image.new("RGB", (1, 1)), image_format)

    with pytest.raises(UnsupportedImageFormatError):
        load_image(source)


def test_load_image_rejects_heif_without_decoder() -> None:
    from pixelmend_engine.imageio import UnsupportedImageFormatError, load_image

    heif_header = BytesIO(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 16)

    with pytest.raises(UnsupportedImageFormatError):
        load_image(heif_header)


@pytest.mark.parametrize("payload", [b"not an image", b"\x89PNG\r\n\x1a\n\x00"])
def test_load_image_rejects_malformed_or_truncated_data(payload: bytes) -> None:
    from pixelmend_engine.imageio import InvalidImageError, load_image

    with pytest.raises(InvalidImageError):
        load_image(BytesIO(payload))


def test_load_image_requires_a_seekable_source() -> None:
    from pixelmend_engine.imageio import InvalidImageError, load_image

    class NonSeekable(BytesIO):
        def seekable(self) -> bool:
            return False

        def seek(self, *args: object, **kwargs: object) -> int:
            raise OSError("not seekable")

    with pytest.raises(InvalidImageError):
        load_image(NonSeekable(b"payload"))


def test_load_image_enforces_source_byte_limit(monkeypatch) -> None:
    import pixelmend_engine.imageio as imageio

    source = _encoded_image(Image.new("RGB", (1, 1)), "PNG")
    monkeypatch.setattr(imageio, "MAX_SOURCE_BYTES", len(source.getvalue()) - 1)

    with pytest.raises(imageio.ImageTooLargeError):
        imageio.load_image(source)


def test_load_image_enforces_pixel_limit(monkeypatch) -> None:
    import pixelmend_engine.imageio as imageio

    source = _encoded_image(Image.new("RGB", (2, 1)), "PNG")
    monkeypatch.setattr(imageio, "MAX_IMAGE_PIXELS", 1)

    with pytest.raises(imageio.ImageTooLargeError):
        imageio.load_image(source)


def test_load_image_promotes_pillow_bomb_warning_to_error(monkeypatch) -> None:
    import pixelmend_engine.imageio as imageio

    source = _encoded_image(Image.new("RGB", (2, 1)), "PNG")
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)

    with pytest.raises(imageio.ImageTooLargeError):
        imageio.load_image(source)


def test_load_image_enforces_frame_limit(monkeypatch) -> None:
    import pixelmend_engine.imageio as imageio

    source = BytesIO()
    Image.new("RGB", (1, 1)).save(
        source,
        format="TIFF",
        save_all=True,
        append_images=[Image.new("RGB", (1, 1))],
    )
    source.seek(0)
    monkeypatch.setattr(imageio, "MAX_IMAGE_FRAMES", 1)

    with pytest.raises(imageio.ImageFrameLimitError):
        imageio.load_image(source)


def test_load_image_enforces_metadata_limit(monkeypatch) -> None:
    import pixelmend_engine.imageio as imageio

    source = _encoded_image(
        Image.new("RGB", (1, 1)),
        "PNG",
        icc_profile=b"oversized-metadata",
    )
    monkeypatch.setattr(imageio, "MAX_METADATA_BYTES", 4)

    with pytest.raises(imageio.ImageMetadataTooLargeError):
        imageio.load_image(source)
