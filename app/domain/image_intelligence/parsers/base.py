from abc import ABC, abstractmethod
import re
from typing import Any

from app.domain.image_intelligence.models import (
    BoundingBox,
    ExtractedAscendant,
    ExtractedChartMetadata,
    ExtractedDashaInfo,
    ExtractedDashaPeriod,
    ExtractedField,
    ExtractedHousePlacement,
    ExtractedPlanetPlacement,
    SourceRegion,
)
from app.domain.image_intelligence.preprocessing import PreprocessedImage
from app.domain.image_intelligence.providers.base import (
    LayoutRegion,
    OCRResult,
    OCRToken,
    VisionLayoutResult,
)

PLANET_CANONICAL_MAP = {
    "SU": "Sun", "SUN": "Sun", "SURYA": "Sun", "RAVI": "Sun", "SY": "Sun", "सूर्य": "Sun", "रवि": "Sun",
    "MO": "Moon", "MOON": "Moon", "CHANDRA": "Moon", "SOMA": "Moon", "CH": "Moon", "चन्द्र": "Moon", "सोम": "Moon",
    "MA": "Mars", "MARS": "Mars", "MANGAL": "Mars", "KUJA": "Mars", "KU": "Mars", "मंगल": "Mars", "कुज": "Mars",
    "ME": "Mercury", "MERCURY": "Mercury", "BUDHA": "Mercury", "BUDH": "Mercury", "BU": "Mercury", "बुध": "Mercury",
    "JU": "Jupiter", "JUPITER": "Jupiter", "GURU": "Jupiter", "BRIHASPATI": "Jupiter", "GU": "Jupiter", "गुरु": "Jupiter",
    "VE": "Venus", "VENUS": "Venus", "SHUKRA": "Venus", "SUKRA": "Venus", "SK": "Venus", "शुक्र": "Venus",
    "SA": "Saturn", "SATURN": "Saturn", "SHANI": "Saturn", "SANI": "Saturn", "SN": "Saturn", "शनि": "Saturn",
    "RA": "Rahu", "RAHU": "Rahu", "NORTH NODE": "Rahu", "राहु": "Rahu",
    "KE": "Ketu", "KETU": "Ketu", "SOUTH NODE": "Ketu", "केतु": "Ketu",
    "ASC": "Ascendant", "ASCENDANT": "Ascendant", "LAGNA": "Ascendant", "LAG": "Ascendant", "AS": "Ascendant", "LA": "Ascendant", "लग्न": "Ascendant",
    "UR": "Uranus", "URANUS": "Uranus", "HARSHAL": "Uranus", "हर्षल": "Uranus",
    "NE": "Neptune", "NEPTUNE": "Neptune", "VARUN": "Neptune", "वरुण": "Neptune",
    "PL": "Pluto", "PLUTO": "Pluto", "YAMA": "Pluto", "यम": "Pluto",
}

SIGN_NUMBER_TO_NAME = {
    1: "Aries", 2: "Taurus", 3: "Gemini", 4: "Cancer",
    5: "Leo", 6: "Virgo", 7: "Libra", 8: "Scorpio",
    9: "Sagittarius", 10: "Capricorn", 11: "Aquarius", 12: "Pisces"
}

SIGN_NAME_TO_NUMBER = {
    "ARIES": 1, "MESHA": 1, "मेष": 1,
    "TAURUS": 2, "VRISHABHA": 2, "वृषभ": 2,
    "GEMINI": 3, "MITHUNA": 3, "मिथुन": 3,
    "CANCER": 4, "KARKA": 4, "कर्क": 4,
    "LEO": 5, "SIMHA": 5, "सिंह": 5,
    "VIRGO": 6, "KANYA": 6, "कन्या": 6,
    "LIBRA": 7, "TULA": 7, "तुला": 7,
    "SCORPIO": 8, "VRISCHIKA": 8, "वृश्चिक": 8,
    "SAGITTARIUS": 9, "DHANU": 9, "धनु": 9,
    "CAPRICORN": 10, "MAKARA": 10, "मकर": 10,
    "AQUARIUS": 11, "KUMBHA": 11, "कुम्भ": 11,
    "PISCES": 12, "MEENA": 12, "मीन": 12,
}


class BaseChartParser(ABC):
    """Abstract base class for topology-specific chart parsers."""

    @abstractmethod
    def parse(
        self,
        vision_result: VisionLayoutResult,
        ocr_result: OCRResult,
        image_info: PreprocessedImage,
    ) -> tuple[
        ExtractedAscendant | None,
        list[ExtractedPlanetPlacement],
        list[ExtractedHousePlacement],
        ExtractedDashaInfo | None,
        ExtractedChartMetadata,
        list[ExtractedField[str]],
    ]:
        """Parse vision regions and OCR tokens into structured astrological placements."""
        pass

    def extract_degree(self, text: str) -> tuple[float | None, str | None]:
        """Extract decimal degree and formatted DMS string from text token."""
        # Match patterns like: 14°20'15", 14:20:15, 14.333, 14deg20min
        dms_match = re.search(r"(\d{1,2})[°:\s](\d{1,2})[':\s]?(\d{1,2})?\"?", text)
        if dms_match:
            deg = int(dms_match.group(1))
            minute = int(dms_match.group(2))
            sec = int(dms_match.group(3)) if dms_match.group(3) else 0
            if 0 <= deg <= 30 and 0 <= minute < 60 and 0 <= sec < 60:
                decimal = deg + (minute / 60.0) + (sec / 3600.0)
                dms_str = f"{deg:02d}°{minute:02d}'{sec:02d}\""
                return decimal, dms_str

        # Decimal degree: e.g. 14.33
        dec_match = re.search(r"(\d{1,2}\.\d+)", text)
        if dec_match:
            val = float(dec_match.group(1))
            if 0.0 <= val <= 30.0:
                return val, f"{val:.2f}°"

        return None, None

    def extract_nakshatra_pada(self, text: str) -> tuple[str | None, int | None]:
        """Extract Nakshatra name and Pada number if present."""
        found_nak: str | None = None
        for nak in [
            "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
            "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
            "Hasta", "Chitra", "Svati", "Vishakha", "Anuradha", "Jyeshtha",
            "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
            "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
        ]:
            if re.search(rf"\b{nak}\b", text, re.IGNORECASE):
                found_nak = nak
                break

        pada: int | None = None
        pada_match = re.search(r"(?:pada|p|चरण)[\s:-]?([1-4])", text, re.IGNORECASE)
        if pada_match:
            pada = int(pada_match.group(1))

        return found_nak, pada

    def extract_common_metadata(self, ocr_result: OCRResult) -> ExtractedChartMetadata:
        """Extract native name, birth date, time, place, ayanamsa from text lines."""
        text = ocr_result.full_text
        meta = ExtractedChartMetadata()

        # Name (within same line)
        name_match = re.search(r"(?:Name|नाम)[\s:-]+([A-Za-z ]+)", text, re.IGNORECASE)
        if name_match:
            meta.native_name = ExtractedField(
                value=name_match.group(1).strip(),
                confidence=0.88,
                extraction_method="ocr_regex_metadata",
            )

        # Date of birth
        dob_match = re.search(r"(?:DOB|Date|दिनांक)[\s:-]+(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{4})", text, re.IGNORECASE)
        if dob_match:
            meta.birth_date = ExtractedField(
                value=dob_match.group(1).strip(),
                confidence=0.90,
                extraction_method="ocr_regex_metadata",
            )

        # Time of birth
        tob_match = re.search(r"(?:TOB|Time|समय)[\s:-]+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)", text, re.IGNORECASE)
        if tob_match:
            meta.birth_time = ExtractedField(
                value=tob_match.group(1).strip(),
                confidence=0.90,
                extraction_method="ocr_regex_metadata",
            )

        # Place (within same line)
        place_match = re.search(r"(?:Place|City|स्थान)[\s:-]+([A-Za-z ,]+)", text, re.IGNORECASE)
        if place_match:
            meta.birth_place = ExtractedField(
                value=place_match.group(1).strip(),
                confidence=0.85,
                extraction_method="ocr_regex_metadata",
            )

        # Ayanamsa (within same line)
        ayan_match = re.search(r"(?:Ayanamsa|Ayanamsha|अयनांश)[\s:-]+([A-Za-z0-9 °'\"]+)", text, re.IGNORECASE)
        if ayan_match:
            meta.ayanamsa = ExtractedField(
                value=ayan_match.group(1).strip(),
                confidence=0.88,
                extraction_method="ocr_regex_metadata",
            )

        # Chart title / label
        title_match = re.search(r"(Lagna Kundli|Rashi Chart|Navamsha|D1|D9|Chalit|Bhava Chart|Horoscope)", text, re.IGNORECASE)
        if title_match:
            meta.chart_title = ExtractedField(
                value=title_match.group(1).strip(),
                confidence=0.95,
                extraction_method="ocr_regex_metadata",
            )

        return meta

