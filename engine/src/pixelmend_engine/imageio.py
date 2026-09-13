"""Decode images into PixelMend's normalized inference asset contract."""

import warnings
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO
from typing import BinaryIO

import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

SUPPORTED_FORMATS = ("JPEG", "PNG", "WEBP", "TIFF")
MAX_SOURCE_BYTES = 256 * 1024 * 1024
MAX_IMAGE_PIXELS = 50_000_000
MAX_IMAGE_FRAMES = 256
MAX_METADATA_BYTES = 4 * 1024 * 1024
_ALPHA_MODES = frozenset({"LA", "La", "PA", "RGBA", "RGBa"})


class ImageIOError(Exception):
    """Base error for safe image decoding and normalization failures."""


class UnsupportedImageModeError(ImageIOError):
    """Raised when normalization would require an undefined tone mapping."""

    def __init__(self, source_mode: str) -> None:
        self.source_mode = source_mode
        super().__init__(f"unsupported image mode: {source_mode}")


class InvalidImageError(ImageIOError):
    """Raised when a source cannot be decoded as one complete image."""


class UnsupportedImageFormatError(ImageIOError):
    """Raised when a recognizable source format is outside the v1 allowlist."""


class ImageTooLargeError(ImageIOError):
    """Raised when encoded bytes or decoded pixels exceed safety limits."""


class ImageFrameLimitError(ImageIOError):
    """Raised before decoding an image with too many frames."""


class ImageMetadataTooLargeError(ImageIOError):
    """Raised before retaining metadata that exceeds the byte budget."""


class ImageWarningCode(StrEnum):
    """Stable machine-readable warning codes returned with imported assets."""

    CMYK_CONVERTED_TO_SRGB = "cmyk_converted_to_srgb"
    BIT_DEPTH_REDUCED_TO_UINT8 = "bit_depth_reduced_to_uint8"
    MULTIFRAME_FIRST_FRAME_ONLY = "multiframe_first_frame_only"
    INVALID_ICC_ASSUMED_SRGB = "invalid_icc_assumed_srgb"


@dataclass(frozen=True, slots=True)
class ImageMetadata:
    """Retain safe source provenance separately from normalized output metadata."""

    source_format: str
    source_mode: str
    source_size: tuple[int, int]
    source_exif: bytes | None
    srgb_icc_profile: bytes


@dataclass(frozen=True, slots=True)
class ImageAsset:
    """Carry one orientation-normalized sRGB image and its detached alpha."""

    rgb: NDArray[np.uint8]
    alpha: NDArray[np.uint8] | None
    metadata: ImageMetadata
    warnings: tuple[ImageWarningCode, ...]

    @property
    def width(self) -> int:
        """Return normalized pixel width."""
        return int(self.rgb.shape[1])

    @property
    def height(self) -> int:
        """Return normalized pixel height."""
        return int(self.rgb.shape[0])


_SRGB_ICC_PROFILE = ImageCms.ImageCmsProfile(
    ImageCms.createProfile("sRGB")
).tobytes()


def _prepare_source(source: BinaryIO) -> bool:
    """Enforce encoded limits and report PNG depth before Pillow reduces it."""
    try:
        if not source.seekable():
            raise OSError("source is not seekable")
        source.seek(0, 2)
        source_size = source.tell()
        source.seek(0)
        prefix = source.read(32)
        source.seek(0)
    except (AttributeError, OSError, ValueError) as error:
        raise InvalidImageError("image source must be seekable") from error

    if source_size > MAX_SOURCE_BYTES:
        raise ImageTooLargeError(
            f"image source exceeds {MAX_SOURCE_BYTES} encoded bytes"
        )
    if (
        prefix.startswith((b"GIF87a", b"GIF89a", b"BM"))
        or len(prefix) >= 12
        and prefix[4:8] == b"ftyp"
    ):
        raise UnsupportedImageFormatError("image format is outside the v1 allowlist")

    return (
        len(prefix) > 24
        and prefix.startswith(b"\x89PNG\r\n\x1a\n")
        and prefix[24] == 16
    )


def _metadata_size(value: object) -> int:
    """Estimate retained Pillow metadata without interpreting untrusted values."""
    if isinstance(value, bytes):
        return len(value)
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    if isinstance(value, dict):
        return sum(
            _metadata_size(key) + _metadata_size(item) for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return sum(_metadata_size(item) for item in value)
    return 0


def load_image(source: BinaryIO) -> ImageAsset:
    """Safely decode one supported source into the normalized asset contract."""
    source_is_16_bit = _prepare_source(source)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            return _decode_image(source, source_is_16_bit=source_is_16_bit)
    except ImageIOError:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as error:
        raise ImageTooLargeError("image exceeds Pillow's decompression limit") from error
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        raise InvalidImageError("image data is malformed or truncated") from error


def _decode_image(source: BinaryIO, *, source_is_16_bit: bool) -> ImageAsset:
    """Decode one supported image into contiguous sRGB-shaped RGB bytes."""
    with Image.open(source, formats=list(SUPPORTED_FORMATS)) as image:
        source_format = image.format
        if source_format is None:
            raise InvalidImageError("decoded image format is unavailable")

        pixel_count = image.width * image.height
        if pixel_count > MAX_IMAGE_PIXELS:
            raise ImageTooLargeError(
                f"image exceeds {MAX_IMAGE_PIXELS} decoded pixels"
            )
        frame_count = getattr(image, "n_frames", 1)
        if frame_count > MAX_IMAGE_FRAMES:
            raise ImageFrameLimitError(
                f"image exceeds {MAX_IMAGE_FRAMES} decoded frames"
            )
        if _metadata_size(image.info) > MAX_METADATA_BYTES:
            raise ImageMetadataTooLargeError(
                f"image metadata exceeds {MAX_METADATA_BYTES} bytes"
            )

        metadata = ImageMetadata(
            source_format=source_format,
            source_mode=image.mode,
            source_size=image.size,
            source_exif=image.info.get("exif"),
            srgb_icc_profile=_SRGB_ICC_PROFILE,
        )
        embedded_icc = image.info.get("icc_profile")
        warning_codes: list[ImageWarningCode] = []
        if frame_count > 1:
            warning_codes.append(ImageWarningCode.MULTIFRAME_FIRST_FRAME_ONLY)
            image.seek(0)

        normalized = ImageOps.exif_transpose(image)
        if _metadata_size(normalized.info) > MAX_METADATA_BYTES:
            raise ImageMetadataTooLargeError(
                f"image metadata exceeds {MAX_METADATA_BYTES} bytes"
            )
        if normalized.mode in {"I", "F"}:
            raise UnsupportedImageModeError(normalized.mode)
        if normalized.mode.startswith("I;16"):
            # Pillow's direct RGB conversion clips values above 255, so reduce
            # the full unsigned range explicitly before creating RGB pixels.
            values = np.asarray(normalized).astype(np.uint32)
            reduced = ((values * 255 + 32_767) // 65_535).astype(np.uint8)
            normalized = Image.fromarray(reduced)
            warning_codes.append(ImageWarningCode.BIT_DEPTH_REDUCED_TO_UINT8)
        elif source_is_16_bit:
            warning_codes.append(ImageWarningCode.BIT_DEPTH_REDUCED_TO_UINT8)

        if normalized.mode == "CMYK":
            warning_codes.append(ImageWarningCode.CMYK_CONVERTED_TO_SRGB)

        has_alpha = (
            normalized.mode in _ALPHA_MODES or "transparency" in normalized.info
        )
        if has_alpha:
            rgba_image = normalized.convert("RGBA")
            alpha = np.asarray(rgba_image.getchannel("A"), dtype=np.uint8).copy(
                order="C"
            )
            color_image = rgba_image.convert("RGB")
        else:
            alpha = None
            color_image = normalized

        if embedded_icc:
            try:
                color_image = ImageCms.profileToProfile(
                    color_image,
                    BytesIO(embedded_icc),
                    ImageCms.createProfile("sRGB"),
                    outputMode="RGB",
                )
            except (ImageCms.PyCMSError, OSError, ValueError):
                warning_codes.append(ImageWarningCode.INVALID_ICC_ASSUMED_SRGB)
                color_image = color_image.convert("RGB")
        else:
            color_image = color_image.convert("RGB")

        rgb = np.asarray(color_image, dtype=np.uint8).copy(order="C")

    return ImageAsset(
        rgb=rgb,
        alpha=alpha,
        metadata=metadata,
        warnings=tuple(warning_codes),
    )


def encode_preview_png(asset: ImageAsset) -> bytes:
    """Encode a normalized asset with sRGB ICC and no source EXIF metadata."""
    preview = Image.fromarray(asset.rgb)
    if asset.alpha is not None:
        preview.putalpha(Image.fromarray(asset.alpha))

    encoded = BytesIO()
    preview.save(
        encoded,
        format="PNG",
        icc_profile=asset.metadata.srgb_icc_profile,
    )
    return encoded.getvalue()


def encode_export(asset: ImageAsset, image_format: str) -> bytes:
    """Export normalized pixels, discarding source metadata and flattening JPEG."""
    if image_format not in SUPPORTED_FORMATS:
        raise UnsupportedImageFormatError('unsupported export format')
    image = Image.fromarray(asset.rgb)
    if asset.alpha is not None:
        image.putalpha(Image.fromarray(asset.alpha))
        if image_format == 'JPEG':
            background = Image.new('RGB', image.size, 'white')
            background.paste(image, mask=image.getchannel('A'))
            image = background
    options = {'icc_profile': asset.metadata.srgb_icc_profile}
    if image_format == 'WEBP':
        options.update(lossless=True, exact=True)
    if image_format == 'JPEG':
        options.update(quality=95, subsampling=0)
    encoded = BytesIO()
    image.save(encoded, format=image_format, **options)
    return encoded.getvalue()
