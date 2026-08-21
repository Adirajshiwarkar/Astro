import io
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.domain.image_intelligence.chart_detector import ChartTypeDetector
from app.domain.image_intelligence.models import (
    BoundingBox,
    ChartType,
    ExtractedAscendant,
    ExtractedField,
    ExtractedHousePlacement,
    ExtractedPlanetPlacement,
    SourceRegion,
    StructuredChartRepresentation,
)
from app.domain.image_intelligence.parsers.dispatcher import ChartParser
from app.domain.image_intelligence.pipeline import ImageIntelligencePipeline
from app.domain.image_intelligence.preprocessing import ImagePreprocessor
from app.domain.image_intelligence.providers.base import (
    LayoutRegion,
    OCRResult,
    OCRToken,
    VisionLayoutResult,
)
from app.domain.image_intelligence.providers.heuristic import (
    HeuristicOCRProvider,
    HeuristicVisionProvider,
)
from app.domain.image_intelligence.providers.mock import (
    MockOCRProvider,
    MockVisionProvider,
)
from app.domain.image_intelligence.security import (
    FileValidationError,
    SecureImageValidator,
)
from app.domain.image_intelligence.validator import ChartExtractionValidator
from app.main import app


def create_sample_png_bytes(width: int = 400, height: int = 400, color: tuple[int, int, int] = (255, 255, 255)) -> bytes:
    """Helper to generate a valid in-memory PNG."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_sample_jpeg_bytes(width: int = 400, height: int = 400) -> bytes:
    """Helper to generate a valid in-memory JPEG."""
    img = Image.new("RGB", (width, height), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_file_validation_magic_bytes_and_security() -> None:
    validator = SecureImageValidator(max_file_size=1024 * 1024, min_dimension=100, max_dimension=2000)

    # Valid PNG
    png_bytes = create_sample_png_bytes(200, 200)
    sanitized, mime, dims = validator.validate_and_sanitize(png_bytes, "image/png")
    assert mime == "image/png"
    assert dims == (200, 200)
    assert len(sanitized) > 0

    # Valid JPEG
    jpeg_bytes = create_sample_jpeg_bytes(300, 300)
    _, mime_jpg, dims_jpg = validator.validate_and_sanitize(jpeg_bytes, "image/jpeg")
    assert mime_jpg == "image/jpeg"
    assert dims_jpg == (300, 300)

    # PDF validation
    pdf_bytes = b"%PDF-1.4 header text data stream test"
    _, mime_pdf, _ = validator.validate_and_sanitize(pdf_bytes, "application/pdf")
    assert mime_pdf == "application/pdf"

    # Empty file
    with pytest.raises(FileValidationError, match="Uploaded file is empty."):
        validator.validate_and_sanitize(b"")

    # Spoofed HTML/Script file disguised as PNG
    html_payload = b"<html><script>alert('xss')</script></html>"
    with pytest.raises(FileValidationError, match="Unsupported or unrecognized file type."):
        validator.validate_and_sanitize(html_payload, "image/png")

    # SVG / XML file rejection
    svg_payload = b"<?xml version='1.0'?><svg xmlns='http://www.w3.org/2000/svg'></svg>"
    with pytest.raises(FileValidationError, match="SVG and XML image formats are prohibited"):
        validator.validate_and_sanitize(svg_payload, "image/svg+xml")

    # Image too small
    tiny_img = create_sample_png_bytes(50, 50)
    with pytest.raises(FileValidationError, match="Image dimensions .* must be within"):
        validator.validate_and_sanitize(tiny_img)

    # Oversized file
    big_validator = SecureImageValidator(max_file_size=100)
    with pytest.raises(FileValidationError, match="exceeds maximum allowed limit"):
        big_validator.validate_and_sanitize(png_bytes)


@pytest.mark.asyncio
async def test_image_preprocessor() -> None:
    preprocessor = ImagePreprocessor()
    png_bytes = create_sample_png_bytes(500, 500)
    preprocessed = preprocessor.preprocess(png_bytes)

    assert preprocessed.dimensions == (500, 500)
    assert preprocessed.grayscale_image is not None
    assert preprocessed.binary_image is not None
    assert preprocessed.enhanced_image is not None
    assert len(preprocessed.regions_of_interest) >= 3


@pytest.mark.asyncio
async def test_chart_type_detector() -> None:
    detector = ChartTypeDetector()
    preprocessor = ImagePreprocessor()
    img_info = preprocessor.preprocess(create_sample_png_bytes())

    # South Indian text indicator
    ocr_south = OCRResult(full_text="South Indian Chart Rashi D1", tokens=[], lines=[])
    vis_res = VisionLayoutResult(detected_chart_type=ChartType.UNKNOWN, chart_confidence=0.0)
    det_south = detector.detect(vis_res, ocr_south, img_info)
    assert det_south.value == ChartType.SOUTH_INDIAN
    assert det_south.confidence > 0.80

    # Western Circular indicator
    ocr_west = OCRResult(full_text="Western Chart Natal Wheel Placidus Houses", tokens=[], lines=[])
    det_west = detector.detect(vis_res, ocr_west, img_info)
    assert det_west.value == ChartType.WESTERN_CIRCULAR

    # Table Report indicator
    ocr_table = OCRResult(full_text="Planet Rashi Degree Nakshatra Pada House Mahadasha Balance", tokens=[], lines=[])
    det_table = detector.detect(vis_res, ocr_table, img_info)
    assert det_table.value == ChartType.TABLE_REPORT

    # North Indian default
    ocr_north = OCRResult(full_text="Lagna Kundli Janma Chart", tokens=[], lines=[])
    det_north = detector.detect(vis_res, ocr_north, img_info)
    assert det_north.value == ChartType.NORTH_INDIAN


@pytest.mark.asyncio
async def test_north_indian_parsing_and_zero_hallucination() -> None:
    # Set up mock vision & OCR for North Indian Kundli
    mock_tokens = [
        OCRToken(text="Lagna Kundli", bbox=BoundingBox(x=100, y=50, width=200, height=30), confidence=0.98),
        OCRToken(text="1", bbox=BoundingBox(x=380, y=200, width=20, height=20), confidence=0.99),
        OCRToken(text="Sun", bbox=BoundingBox(x=360, y=230, width=40, height=20), confidence=0.97),
        OCRToken(text="14°20'15\"", bbox=BoundingBox(x=360, y=250, width=50, height=20), confidence=0.95),
        OCRToken(text="Ashwini", bbox=BoundingBox(x=360, y=270, width=60, height=20), confidence=0.94),
        OCRToken(text="Pada 2", bbox=BoundingBox(x=360, y=290, width=50, height=20), confidence=0.94),
        OCRToken(text="Moon", bbox=BoundingBox(x=200, y=180, width=40, height=20), confidence=0.96),
        OCRToken(text="Jupiter", bbox=BoundingBox(x=500, y=400, width=40, height=20), confidence=0.95),
    ]
    mock_full_text = "Lagna Kundli 1 Sun 14°20'15\" Ashwini Pada 2 Moon Jupiter"

    pipeline = ImageIntelligencePipeline(
        vision_provider=MockVisionProvider(chart_type=ChartType.NORTH_INDIAN, chart_confidence=0.96),
        ocr_provider=MockOCRProvider(mock_tokens=mock_tokens, mock_full_text=mock_full_text),
    )

    sample_bytes = create_sample_png_bytes(800, 800)
    res: StructuredChartRepresentation = await pipeline.process_image(sample_bytes)

    assert res.chart_type.value == ChartType.NORTH_INDIAN
    assert res.ascendant is not None
    assert res.ascendant.sign.value == "Aries"
    assert res.ascendant.sign_number is not None and res.ascendant.sign_number.value == 1

    # Check extracted planets
    planet_names = [p.planet.value for p in res.planets]
    assert "Sun" in planet_names
    assert "Moon" in planet_names
    assert "Jupiter" in planet_names

    # Check Sun degree, nakshatra, and pada
    sun_placement = next(p for p in res.planets if p.planet.value == "Sun")
    assert sun_placement.degree is not None
    assert round(sun_placement.degree.value, 2) == 14.34
    assert sun_placement.degree_dms is not None and sun_placement.degree_dms.value == "14°20'15\""
    assert sun_placement.nakshatra is not None and sun_placement.nakshatra.value == "Ashwini"
    assert sun_placement.pada is not None and sun_placement.pada.value == 2

    # Zero-hallucination verification: Dasha was not in image, so it must be None (never guessed)
    assert res.dasha is None

    # Verify provenance and schema on every field
    for p in res.planets:
        assert isinstance(p.planet, ExtractedField)
        assert 0.0 <= p.planet.confidence <= 1.0
        assert p.planet.extraction_method != ""
        if p.house:
            assert 1 <= p.house.value <= 12

    assert len(res.houses) == 12
    assert res.overall_confidence > 0.80
    assert res.validation_summary.get("is_valid") is True


@pytest.mark.asyncio
async def test_south_indian_chart_parsing() -> None:
    mock_tokens = [
        OCRToken(text="South Indian Chart", bbox=BoundingBox(x=100, y=50, width=200, height=30), confidence=0.98),
        OCRToken(text="Asc", bbox=BoundingBox(x=120, y=120, width=30, height=20), confidence=0.97),
        OCRToken(text="Mars", bbox=BoundingBox(x=120, y=150, width=40, height=20), confidence=0.95),
        OCRToken(text="Venus", bbox=BoundingBox(x=200, y=120, width=40, height=20), confidence=0.96),
    ]
    mock_full_text = "South Indian Chart Asc Mars Venus"

    pipeline = ImageIntelligencePipeline(
        vision_provider=MockVisionProvider(chart_type=ChartType.SOUTH_INDIAN, chart_confidence=0.94),
        ocr_provider=MockOCRProvider(mock_tokens=mock_tokens, mock_full_text=mock_full_text),
    )

    sample_bytes = create_sample_png_bytes()
    res = await pipeline.process_image(sample_bytes)

    assert res.chart_type.value == ChartType.SOUTH_INDIAN
    assert res.ascendant is not None
    assert res.ascendant.sign.value == "Aries"
    planet_names = [p.planet.value for p in res.planets]
    assert "Mars" in planet_names
    assert "Venus" in planet_names
    assert len(res.houses) == 12


@pytest.mark.asyncio
async def test_table_report_parsing_with_dasha() -> None:
    table_text = """
    Kundli Planetary Details
    Name: John Doe
    DOB: 1990-10-12
    TOB: 14:30
    Place: Mumbai, India
    Ayanamsa: Lahiri 23:43:40
    Ascendant Mesha 14:20:15 Ashwini 2 1
    Sun Kanya 25:10:00 Chitra 1 6 (R)
    Moon Vrishabha 05:30:00 Krittika 3 2
    Mars Simha 12:00:00 Magha 4 5 (C)
    Balance of Dasha: Venus 12y 4m 15d
    Mahadasha: Saturn
    Antardasha: Mercury
    """
    lines = [l.strip() for l in table_text.strip().splitlines()]
    tokens = [OCRToken(text=word, confidence=0.95) for line in lines for word in line.split()]

    pipeline = ImageIntelligencePipeline(
        vision_provider=MockVisionProvider(chart_type=ChartType.TABLE_REPORT, chart_confidence=0.92),
        ocr_provider=MockOCRProvider(mock_tokens=tokens, mock_full_text=table_text),
    )

    sample_bytes = create_sample_png_bytes()
    res = await pipeline.process_image(sample_bytes)

    assert res.chart_type.value == ChartType.TABLE_REPORT
    assert res.metadata.native_name is not None and res.metadata.native_name.value == "John Doe"
    assert res.metadata.birth_date is not None and res.metadata.birth_date.value == "1990-10-12"
    assert res.metadata.birth_place is not None and res.metadata.birth_place.value == "Mumbai, India"

    # Ascendant
    assert res.ascendant is not None
    assert res.ascendant.sign.value == "Aries"

    # Planets
    planets = {p.planet.value: p for p in res.planets}
    assert "Sun" in planets
    assert planets["Sun"].sign is not None and planets["Sun"].sign.value == "Virgo"
    assert planets["Sun"].house is not None and planets["Sun"].house.value == 6
    assert planets["Sun"].is_retrograde is not None and planets["Sun"].is_retrograde.value is True

    assert "Moon" in planets
    assert planets["Moon"].sign is not None and planets["Moon"].sign.value == "Taurus"
    assert planets["Moon"].house is not None and planets["Moon"].house.value == 2

    assert "Mars" in planets
    assert planets["Mars"].is_combust is not None and planets["Mars"].is_combust.value is True

    # Dasha info
    assert res.dasha is not None
    assert res.dasha.balance_at_birth is not None and "Venus" in res.dasha.balance_at_birth.value
    assert res.dasha.current_mahadasha is not None and res.dasha.current_mahadasha.value == "Saturn"
    assert res.dasha.current_antardasha is not None and res.dasha.current_antardasha.value == "Mercury"


@pytest.mark.asyncio
async def test_western_circular_chart_parsing() -> None:
    wheel_text = "Western Chart Natal Wheel Sun 15:00:00 Moon 22:30:00 Placidus"
    tokens = [OCRToken(text=w, confidence=0.92) for w in wheel_text.split()]

    pipeline = ImageIntelligencePipeline(
        vision_provider=MockVisionProvider(chart_type=ChartType.WESTERN_CIRCULAR, chart_confidence=0.95),
        ocr_provider=MockOCRProvider(mock_tokens=tokens, mock_full_text=wheel_text),
    )

    sample_bytes = create_sample_png_bytes()
    res = await pipeline.process_image(sample_bytes)

    assert res.chart_type.value == ChartType.WESTERN_CIRCULAR
    assert res.ascendant is not None
    assert len(res.houses) == 12
    assert any(h.cusp_degree is not None for h in res.houses)


@pytest.mark.asyncio
async def test_chart_validator_anomalies_and_checks() -> None:
    validator = ChartExtractionValidator()

    # Valid chart representation
    valid_chart = StructuredChartRepresentation(
        chart_type=ExtractedField(value=ChartType.NORTH_INDIAN, confidence=0.95, extraction_method="test"),
        ascendant=ExtractedAscendant(
            sign=ExtractedField(value="Aries", confidence=0.95, extraction_method="test"),
            sign_number=ExtractedField(value=1, confidence=0.95, extraction_method="test"),
            degree=ExtractedField(value=10.5, confidence=0.90, extraction_method="test"),
        ),
        planets=[
            ExtractedPlanetPlacement(
                planet=ExtractedField(value="Sun", confidence=0.95, extraction_method="test"),
                sign=ExtractedField(value="Aries", confidence=0.95, extraction_method="test"),
                sign_number=ExtractedField(value=1, confidence=0.95, extraction_method="test"),
                house=ExtractedField(value=1, confidence=0.95, extraction_method="test"),
                degree=ExtractedField(value=14.2, confidence=0.90, extraction_method="test"),
                nakshatra=ExtractedField(value="Ashwini", confidence=0.90, extraction_method="test"),
                pada=ExtractedField(value=2, confidence=0.90, extraction_method="test"),
            )
        ],
        houses=[
            ExtractedHousePlacement(
                house_number=ExtractedField(value=i, confidence=0.95, extraction_method="test")
            )
            for i in range(1, 13)
        ],
        overall_confidence=0.95,
    )
    val_res = validator.validate(valid_chart)
    assert val_res["is_valid"] is True
    assert len(val_res["errors"]) == 0

    # Chart with invalid degree (> 30) and duplicate planet
    invalid_chart = StructuredChartRepresentation(
        chart_type=ExtractedField(value=ChartType.NORTH_INDIAN, confidence=0.95, extraction_method="test"),
        ascendant=ExtractedAscendant(
            sign=ExtractedField(value="Aries", confidence=0.95, extraction_method="test"),
            degree=ExtractedField(value=35.0, confidence=0.90, extraction_method="test"),  # Invalid
        ),
        planets=[
            ExtractedPlanetPlacement(
                planet=ExtractedField(value="Sun", confidence=0.95, extraction_method="test"),
                degree=ExtractedField(value=45.0, confidence=0.90, extraction_method="test"),  # Invalid
                pada=ExtractedField(value=6, confidence=0.90, extraction_method="test"),  # Invalid pada
            ),
            ExtractedPlanetPlacement(
                planet=ExtractedField(value="Sun", confidence=0.95, extraction_method="test"),  # Duplicate
            ),
        ],
        houses=[],
        overall_confidence=0.50,
    )
    invalid_val_res = validator.validate(invalid_chart)
    assert invalid_val_res["is_valid"] is False
    assert len(invalid_val_res["errors"]) >= 2
    assert any("Duplicate" in w for w in invalid_val_res["warnings"])


@pytest.mark.asyncio
async def test_provider_swappability() -> None:
    """Ensure VisionProvider and OCRProvider can be dynamically swapped without breaking pipeline."""
    h_vis = HeuristicVisionProvider()
    h_ocr = HeuristicOCRProvider(fallback_text="Lagna Kundli Sun Moon")
    custom_pipeline = ImageIntelligencePipeline(vision_provider=h_vis, ocr_provider=h_ocr)

    sample_bytes = create_sample_png_bytes()
    res = await custom_pipeline.process_image(sample_bytes)
    assert isinstance(res, StructuredChartRepresentation)
    assert res.chart_type.value == ChartType.NORTH_INDIAN


@pytest.mark.asyncio
async def test_chart_upload_api_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Success upload
        png_bytes = create_sample_png_bytes(300, 300)
        files = {"file": ("kundli.png", png_bytes, "image/png")}
        response = await client.post("/api/v1/charts/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "chart_data" in data
        assert data["chart_data"]["chart_type"]["value"] in ["north_indian", "south_indian", "table_report", "western_circular", "east_indian", "unknown"]

        # 2. Reject empty file
        empty_files = {"file": ("empty.png", b"", "image/png")}
        empty_resp = await client.post("/api/v1/charts/upload", files=empty_files)
        assert empty_resp.status_code == 400

        # 3. Reject spoofed malicious payload
        bad_files = {"file": ("bad.png", b"<!DOCTYPE html><script>bad()</script>", "image/png")}
        bad_resp = await client.post("/api/v1/charts/upload", files=bad_files)
        assert bad_resp.status_code == 400
