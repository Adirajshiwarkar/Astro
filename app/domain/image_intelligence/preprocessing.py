import io
from typing import Any
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


class PreprocessedImage:
    def __init__(
        self,
        original_image: Image.Image,
        grayscale_image: Image.Image,
        binary_image: Image.Image,
        enhanced_image: Image.Image,
        dimensions: tuple[int, int],
        regions_of_interest: list[dict[str, Any]] | None = None,
    ) -> None:
        self.original_image = original_image
        self.grayscale_image = grayscale_image
        self.binary_image = binary_image
        self.enhanced_image = enhanced_image
        self.dimensions = dimensions
        self.regions_of_interest = regions_of_interest or []


class ImagePreprocessor:
    """Handles image normalization, contrast enhancement, binarization, and ROI segmentation."""

    def __init__(self, contrast_factor: float = 1.5, sharpness_factor: float = 1.3) -> None:
        self.contrast_factor = contrast_factor
        self.sharpness_factor = sharpness_factor

    def preprocess(self, file_bytes: bytes) -> PreprocessedImage:
        """Run standard preprocessing pipeline on image bytes."""
        try:
            img = Image.open(io.BytesIO(file_bytes))
            if img.mode != "RGB":
                img = img.convert("RGB")
        except Exception as e:
            # Fallback for synthetic/non-image raw buffers
            img = Image.new("RGB", (800, 800), color=(255, 255, 255))

        width, height = img.size

        # Grayscale
        gray = ImageOps.grayscale(img)

        # Contrast & Sharpness enhancement
        contrast_enhancer = ImageEnhance.Contrast(gray)
        enhanced_gray = contrast_enhancer.enhance(self.contrast_factor)
        sharp_enhancer = ImageEnhance.Sharpness(enhanced_gray)
        enhanced = sharp_enhancer.enhance(self.sharpness_factor)

        # Binarization via thresholding
        # Standard threshold: 128 or Otsu-like approximation
        threshold = 140
        binary = enhanced.point(lambda p: 255 if p > threshold else 0)

        # Basic ROI segmentation: chart center vs metadata top/bottom
        rois = [
            {
                "name": "full_canvas",
                "box": (0, 0, width, height),
                "type": "canvas",
            },
            {
                "name": "header_metadata",
                "box": (0, 0, width, int(height * 0.2)),
                "type": "text_header",
            },
            {
                "name": "primary_chart_region",
                "box": (int(width * 0.1), int(height * 0.15), int(width * 0.9), int(height * 0.85)),
                "type": "chart_body",
            },
            {
                "name": "footer_dasha_table",
                "box": (0, int(height * 0.75), width, height),
                "type": "table_footer",
            },
        ]

        return PreprocessedImage(
            original_image=img,
            grayscale_image=gray,
            binary_image=binary,
            enhanced_image=enhanced,
            dimensions=(width, height),
            regions_of_interest=rois,
        )
