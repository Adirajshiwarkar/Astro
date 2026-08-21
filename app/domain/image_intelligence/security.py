import io
from typing import BinaryIO
from PIL import Image

# Magic byte signatures
MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/webp": [b"RIFF"],  # Further verified by WEBP at offset 8
    "application/pdf": [b"%PDF-"],
    "image/tiff": [b"II*\x00", b"MM\x00*"],
    "image/bmp": [b"BM"],
}

# Blocked dangerous types
DANGEROUS_MIMES = {
    "image/svg+xml",  # SVG can contain embedded JavaScript / XML external entities
    "text/html",
    "application/javascript",
    "application/x-executable",
    "application/x-sh",
}

DEFAULT_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_MIN_DIMENSION = 100  # 100 px
DEFAULT_MAX_DIMENSION = 8000  # 8000 px
DEFAULT_MAX_TOTAL_PIXELS = 30_000_000  # 30 Megapixels max (decompression bomb protection)

# Configure PIL decompression bomb ceiling
Image.MAX_IMAGE_PIXELS = DEFAULT_MAX_TOTAL_PIXELS


class FileValidationError(ValueError):
    """Raised when file fails security validation."""
    pass


class SecureImageValidator:
    """Validates uploaded images and documents for MIME type, dimensions, file size,

    and guards against decompression bombs and malicious payload embedding.
    """

    def __init__(
        self,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        min_dimension: int = DEFAULT_MIN_DIMENSION,
        max_dimension: int = DEFAULT_MAX_DIMENSION,
        max_total_pixels: int = DEFAULT_MAX_TOTAL_PIXELS,
    ) -> None:
        self.max_file_size = max_file_size
        self.min_dimension = min_dimension
        self.max_dimension = max_dimension
        self.max_total_pixels = max_total_pixels

    def detect_mime_from_magic_bytes(self, data: bytes) -> str:
        """Inspect binary header magic bytes to verify true file format."""
        if len(data) < 12:
            raise FileValidationError("File payload too small to determine format.")

        for mime, sigs in MAGIC_SIGNATURES.items():
            for sig in sigs:
                if data.startswith(sig):
                    if mime == "image/webp":
                        # Check WEBP sub-header at index 8
                        if data[8:12] != b"WEBP":
                            continue
                    return mime

        # Check for SVG script / XML injection
        first_chunk = data[:512].lower()
        if b"<svg" in first_chunk or b"<?xml" in first_chunk:
            raise FileValidationError(
                "SVG and XML image formats are prohibited due to script injection risks."
            )

        raise FileValidationError(
            "Unsupported or unrecognized file type. Supported formats: PNG, JPEG, WEBP, PDF, TIFF, BMP."
        )

    def validate_and_sanitize(
        self, file_bytes: bytes, declared_mime: str | None = None
    ) -> tuple[bytes, str, tuple[int, int]]:
        """Validate file size, magic bytes, dimensions, and strip metadata.

        Returns (sanitized_bytes, detected_mime, (width, height)).
        """
        # 1. File size check
        if len(file_bytes) == 0:
            raise FileValidationError("Uploaded file is empty.")
        if len(file_bytes) > self.max_file_size:
            raise FileValidationError(
                f"File size {len(file_bytes)} bytes exceeds maximum allowed limit of {self.max_file_size} bytes."
            )

        # 2. Magic byte verification
        detected_mime = self.detect_mime_from_magic_bytes(file_bytes)

        if declared_mime and declared_mime.lower() in DANGEROUS_MIMES:
            raise FileValidationError(f"Prohibited file type: {declared_mime}")

        # 3. PDF handling
        if detected_mime == "application/pdf":
            # PDF is validated as document
            return file_bytes, detected_mime, (0, 0)

        # 4. Image inspection and dimension limits
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                img.verify()
        except Exception as e:
            raise FileValidationError(f"Corrupted or invalid image data: {e}") from e

        # Reopen image for dimension extraction & sanitization
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                width, height = img.size
                total_pixels = width * height

                if total_pixels > self.max_total_pixels:
                    raise FileValidationError(
                        f"Image pixel count {total_pixels} exceeds maximum limit of {self.max_total_pixels} (Decompression Bomb Protection)."
                    )

                if (
                    width < self.min_dimension
                    or height < self.min_dimension
                    or width > self.max_dimension
                    or height > self.max_dimension
                ):
                    raise FileValidationError(
                        f"Image dimensions ({width}x{height}) must be within [{self.min_dimension}x{self.min_dimension}, {self.max_dimension}x{self.max_dimension}]."
                    )

                # 5. Metadata sanitization: create a clean image without EXIF/ancillary chunks
                img_format = img.format or "PNG"
                clean_img = img.copy()
                clean_img.info = {}  # Clear EXIF / metadata dictionary

                out_buf = io.BytesIO()
                clean_img.save(out_buf, format=img_format)
                sanitized_bytes = out_buf.getvalue()

                return sanitized_bytes, detected_mime, (width, height)

        except FileValidationError:
            raise
        except Exception as e:
            raise FileValidationError(f"Failed to process and sanitize image: {e}") from e
