import pytest

from app.domain.astrology.models import (
    HousePlacement,
    PlanetPlacement,
    WesternChart,
)
from app.domain.canonical.comparator import ChartComparator
from app.domain.canonical.models import (
    CanonicalChartMetadata,
    CanonicalChartRepresentation,
    CanonicalField,
    CanonicalHousePlacement,
    CanonicalPlanetPlacement,
    CanonicalPointPlacement,
    ComparisonStatus,
    ProvenanceMetadata,
    ValidationStatus,
)
from app.domain.canonical.normalizer import ChartNormalizer
from app.domain.canonical.validation_service import ChartValidationService
from app.domain.image_intelligence.models import (
    BoundingBox,
    ChartType,
    ExtractedAscendant,
    ExtractedChartMetadata,
    ExtractedField,
    ExtractedHousePlacement,
    ExtractedPlanetPlacement,
    SourceRegion,
    StructuredChartRepresentation,
)
from app.domain.vedic.models import (
    BhavaPlacement,
    GrahaPlacement,
    VedicCalculationMetadata,
    VedicChart,
)


def create_sample_calculated_canonical_chart() -> CanonicalChartRepresentation:
    prov = ProvenanceMetadata(
        source="ephemeris_calculation",
        method="swiss_ephemeris",
        confidence=1.0,
        engine_version="1.0.0",
        calculation_config={"ayanamsa": "lahiri", "house_system": "placidus"},
    )
    asc = CanonicalPointPlacement(
        name=CanonicalField(value="Ascendant", provenance=prov),
        sign=CanonicalField(value="Aries", provenance=prov),
        sign_number=CanonicalField(value=1, provenance=prov),
        degree=CanonicalField(value=14.333, provenance=prov),
        total_longitude=CanonicalField(value=14.333, provenance=prov),
    )
    planets = {
        "Sun": CanonicalPlanetPlacement(
            planet=CanonicalField(value="Sun", provenance=prov),
            sign=CanonicalField(value="Aries", provenance=prov),
            sign_number=CanonicalField(value=1, provenance=prov),
            degree=CanonicalField(value=14.333, provenance=prov),
            total_longitude=CanonicalField(value=14.333, provenance=prov),
            house=CanonicalField(value=1, provenance=prov),
            is_retrograde=CanonicalField(value=False, provenance=prov),
        ),
        "Moon": CanonicalPlanetPlacement(
            planet=CanonicalField(value="Moon", provenance=prov),
            sign=CanonicalField(value="Taurus", provenance=prov),
            sign_number=CanonicalField(value=2, provenance=prov),
            degree=CanonicalField(value=5.500, provenance=prov),
            total_longitude=CanonicalField(value=35.500, provenance=prov),
            house=CanonicalField(value=2, provenance=prov),
            is_retrograde=CanonicalField(value=False, provenance=prov),
        ),
    }
    houses = [
        CanonicalHousePlacement(
            house_number=CanonicalField(value=i, provenance=prov),
            sign=CanonicalField(value="Aries", provenance=prov),
            sign_number=CanonicalField(value=1, provenance=prov),
        )
        for i in range(1, 13)
    ]
    return CanonicalChartRepresentation(
        zodiac_system="sidereal",
        ascendant=asc,
        planets=planets,
        houses=houses,
        provenance=prov,
    )


def test_chart_normalizer_from_image_extraction() -> None:
    normalizer = ChartNormalizer()
    img_chart = StructuredChartRepresentation(
        chart_type=ExtractedField(value=ChartType.NORTH_INDIAN, confidence=0.95, extraction_method="vision"),
        ascendant=ExtractedAscendant(
            sign=ExtractedField(value="Aries", confidence=0.92, extraction_method="ocr"),
            sign_number=ExtractedField(value=1, confidence=0.92, extraction_method="ocr"),
            degree=ExtractedField(value=14.33, confidence=0.90, extraction_method="ocr"),
        ),
        planets=[
            ExtractedPlanetPlacement(
                planet=ExtractedField(
                    value="Sun",
                    confidence=0.95,
                    source_region=SourceRegion(bbox=BoundingBox(x=10, y=10, width=50, height=20)),
                    extraction_method="ocr",
                ),
                sign=ExtractedField(value="Aries", confidence=0.90, extraction_method="ocr"),
                sign_number=ExtractedField(value=1, confidence=0.90, extraction_method="ocr"),
                house=ExtractedField(value=1, confidence=0.90, extraction_method="vision"),
                degree=ExtractedField(value=14.33, confidence=0.90, extraction_method="ocr"),
                is_retrograde=ExtractedField(value=False, confidence=0.90, extraction_method="ocr"),
            )
        ],
        houses=[
            ExtractedHousePlacement(
                house_number=ExtractedField(value=i, confidence=0.95, extraction_method="vision")
            )
            for i in range(1, 13)
        ],
        overall_confidence=0.93,
    )

    canonical = normalizer.from_image_extraction(img_chart)
    assert canonical.ascendant is not None
    assert canonical.ascendant.sign.value == "Aries"
    assert canonical.ascendant.sign.provenance.source == "image_extraction"
    assert canonical.ascendant.sign.provenance.confidence == 0.92

    assert "Sun" in canonical.planets
    sun = canonical.planets["Sun"]
    assert sun.planet.value == "Sun"
    assert sun.planet.provenance.source_region is not None
    assert sun.house is not None and sun.house.value == 1


def test_chart_normalizer_from_vedic_and_western() -> None:
    normalizer = ChartNormalizer()

    # Normalize VedicChart
    v_chart = VedicChart(
        lagna="Mesha",
        lagna_degree=15.5,
        grahas=[
            GrahaPlacement(
                vedic_name="Surya",
                western_name="Sun",
                longitude=14.2,
                latitude=0.0,
                speed=1.0,
                is_retrograde=False,
                rashi="Mesha",
                rashi_degree=14.2,
                bhava=1,
                nakshatra="Ashwini",
                nakshatra_pada=1,
            )
        ],
        bhavas=[
            BhavaPlacement(number=i, cusp=float((i - 1) * 30), rashi="Mesha", rashi_degree=0.0)
            for i in range(1, 13)
        ],
        aspects=[],
        vimshottari_dasha=[],
        metadata=VedicCalculationMetadata(
            methodology="Parashari System",
            ayanamsa="lahiri",
            calculation_timestamp="2026-08-18T00:00:00",
            engine_version="1.0.0",
        ),
    )
    canonical_v = normalizer.from_vedic_chart(v_chart)
    assert canonical_v.ascendant is not None
    assert canonical_v.ascendant.sign.value == "Aries"
    assert "Sun" in canonical_v.planets
    assert canonical_v.planets["Sun"].nakshatra is not None and canonical_v.planets["Sun"].nakshatra.value == "Ashwini"

    # Normalize WesternChart
    w_chart = WesternChart(
        placements=[
            PlanetPlacement(
                name="Sun",
                longitude=15.0,
                latitude=0.0,
                speed=1.0,
                is_retrograde=False,
                sign="Aries",
                sign_degree=15.0,
                house=1,
            )
        ],
        houses=[
            HousePlacement(number=i, cusp=float((i - 1) * 30), sign="Aries", sign_degree=0.0)
            for i in range(1, 13)
        ],
        ascendant=15.0,
        mc=105.0,
        aspects=[],
        derived_factors=[],
    )
    canonical_w = normalizer.from_western_chart(w_chart)
    assert canonical_w.ascendant is not None
    assert canonical_w.ascendant.sign.value == "Aries"
    assert canonical_w.midheaven is not None and canonical_w.midheaven.sign.value == "Cancer"


def test_matching_charts_validation() -> None:
    service = ChartValidationService()
    calculated_chart = create_sample_calculated_canonical_chart()

    # Create matching image extraction chart
    img_prov = ProvenanceMetadata(
        source="image_extraction",
        method="ocr_vision",
        confidence=0.95,
        engine_version="1.0.0",
    )
    img_chart = CanonicalChartRepresentation(
        zodiac_system="sidereal",
        ascendant=CanonicalPointPlacement(
            name=CanonicalField(value="Ascendant", provenance=img_prov),
            sign=CanonicalField(value="Aries", provenance=img_prov),
            sign_number=CanonicalField(value=1, provenance=img_prov),
            degree=CanonicalField(value=14.30, provenance=img_prov),  # Within 1.0 deg tolerance
        ),
        planets={
            "Sun": CanonicalPlanetPlacement(
                planet=CanonicalField(value="Sun", provenance=img_prov),
                sign=CanonicalField(value="Aries", provenance=img_prov),
                sign_number=CanonicalField(value=1, provenance=img_prov),
                degree=CanonicalField(value=14.30, provenance=img_prov),
                house=CanonicalField(value=1, provenance=img_prov),
                is_retrograde=CanonicalField(value=False, provenance=img_prov),
            ),
            "Moon": CanonicalPlanetPlacement(
                planet=CanonicalField(value="Moon", provenance=img_prov),
                sign=CanonicalField(value="Taurus", provenance=img_prov),
                sign_number=CanonicalField(value=2, provenance=img_prov),
                degree=CanonicalField(value=5.50, provenance=img_prov),
                house=CanonicalField(value=2, provenance=img_prov),
                is_retrograde=CanonicalField(value=False, provenance=img_prov),
            ),
        },
        houses=[
            CanonicalHousePlacement(
                house_number=CanonicalField(value=i, provenance=img_prov),
                sign=CanonicalField(value="Aries", provenance=img_prov),
                sign_number=CanonicalField(value=1, provenance=img_prov),
            )
            for i in range(1, 13)
        ],
        provenance=img_prov,
    )

    report = service.validate_dual_sources(img_chart, calculated_chart)

    assert report.status == ValidationStatus.VERIFIED
    assert report.match_percentage == 100.0
    assert len(report.conflicts) == 0
    assert len(report.matching_fields) >= 5


def test_conflicting_charts_validation_no_overwrite() -> None:
    service = ChartValidationService()
    calculated_chart = create_sample_calculated_canonical_chart()

    # Image chart with Sun in Taurus (House 2) instead of Aries (House 1)
    img_prov = ProvenanceMetadata(
        source="image_extraction",
        method="ocr_vision",
        confidence=0.90,
        engine_version="1.0.0",
    )
    conflicting_img_chart = CanonicalChartRepresentation(
        zodiac_system="sidereal",
        ascendant=CanonicalPointPlacement(
            name=CanonicalField(value="Ascendant", provenance=img_prov),
            sign=CanonicalField(value="Aries", provenance=img_prov),
            sign_number=CanonicalField(value=1, provenance=img_prov),
        ),
        planets={
            "Sun": CanonicalPlanetPlacement(
                planet=CanonicalField(value="Sun", provenance=img_prov),
                sign=CanonicalField(value="Taurus", provenance=img_prov),  # Conflicting sign!
                sign_number=CanonicalField(value=2, provenance=img_prov),
                house=CanonicalField(value=2, provenance=img_prov),       # Conflicting house!
            ),
        },
        houses=[],
        provenance=img_prov,
    )

    report = service.validate_dual_sources(conflicting_img_chart, calculated_chart)

    assert report.status == ValidationStatus.DISCREPANCIES_FOUND
    assert len(report.conflicts) >= 2  # Sun sign and Sun house conflict
    assert report.match_percentage < 100.0

    # Ensure neither source is overwritten
    conflict_sign = next(c for c in report.conflicts if c.field_name == "Planet[Sun].sign")
    assert conflict_sign.value_a == "Taurus"
    assert conflict_sign.provenance_a is not None and conflict_sign.provenance_a.source == "image_extraction"
    assert conflict_sign.value_b == "Aries"
    assert conflict_sign.provenance_b is not None and conflict_sign.provenance_b.source == "ephemeris_calculation"


def test_partial_charts_and_missing_data() -> None:
    service = ChartValidationService()
    calculated_chart = create_sample_calculated_canonical_chart()

    # Partial image chart containing only Moon, missing Sun
    img_prov = ProvenanceMetadata(
        source="image_extraction",
        method="ocr_vision",
        confidence=0.90,
        engine_version="1.0.0",
    )
    partial_chart = CanonicalChartRepresentation(
        zodiac_system="sidereal",
        planets={
            "Moon": CanonicalPlanetPlacement(
                planet=CanonicalField(value="Moon", provenance=img_prov),
                sign=CanonicalField(value="Taurus", provenance=img_prov),
                sign_number=CanonicalField(value=2, provenance=img_prov),
                house=CanonicalField(value=2, provenance=img_prov),
            )
        },
        houses=[],
        provenance=img_prov,
    )

    report = service.validate_dual_sources(partial_chart, calculated_chart)

    assert report.status in (ValidationStatus.PARTIAL_MATCH, ValidationStatus.VERIFIED)
    assert len(report.missing_fields) >= 1
    # Sun was missing in image (Source A)
    missing_sun = next(m for m in report.missing_fields if "Sun" in m.field_name)
    assert missing_sun.status == ComparisonStatus.MISSING_IN_A


def test_low_confidence_ocr_flagging() -> None:
    service = ChartValidationService()
    calculated_chart = create_sample_calculated_canonical_chart()

    # Low confidence image extraction (< 0.75 threshold)
    low_conf_prov = ProvenanceMetadata(
        source="image_extraction",
        method="blurred_ocr",
        confidence=0.55,  # Low confidence!
        engine_version="1.0.0",
    )
    low_conf_chart = CanonicalChartRepresentation(
        zodiac_system="sidereal",
        planets={
            "Sun": CanonicalPlanetPlacement(
                planet=CanonicalField(value="Sun", provenance=low_conf_prov),
                sign=CanonicalField(value="Aries", provenance=low_conf_prov),
                sign_number=CanonicalField(value=1, provenance=low_conf_prov),
                house=CanonicalField(value=1, provenance=low_conf_prov),
            ),
        },
        houses=[],
        provenance=low_conf_prov,
    )

    report = service.validate_dual_sources(low_conf_chart, calculated_chart)

    assert report.status == ValidationStatus.HIGH_UNCERTAINTY
    assert len(report.low_confidence_fields) >= 1
    assert any(lc.status == ComparisonStatus.LOW_CONFIDENCE for lc in report.low_confidence_fields)
