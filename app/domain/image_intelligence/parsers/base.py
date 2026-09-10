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

PLANET_CANONICAL_MAP: dict[str, str] = {
    # Sun
    "SU": "Sun", "SUN": "Sun", "SURYA": "Sun", "RAVI": "Sun", "SY": "Sun", "SO": "Sun", "SOL": "Sun", "SUR": "Sun", "RAV": "Sun",
    "सूर्य": "Sun", "रवि": "Sun", "सूरज": "Sun", "भास्कर": "Sun", "दिनेश": "Sun", "सू": "Sun", "र": "Sun",
    # Moon
    "MO": "Moon", "MOON": "Moon", "CHANDRA": "Moon", "SOMA": "Moon", "CH": "Moon", "MN": "Moon", "LUN": "Moon", "LUNA": "Moon",
    "SOM": "Moon", "CHN": "Moon", "चन्द्र": "Moon", "चंद्र": "Moon", "सोम": "Moon", "चंदा": "Moon", "चं": "Moon", "सो": "Moon",
    # Mars
    "MA": "Mars", "MARS": "Mars", "MANGAL": "Mars", "KUJA": "Mars", "ANGARAKA": "Mars", "KU": "Mars", "KJ": "Mars", "MR": "Mars",
    "MNG": "Mars", "KUJ": "Mars", "मंगल": "Mars", "मङ्गल": "Mars", "कुज": "Mars", "अंगारक": "Mars", "भौम": "Mars", "मं": "Mars", "कु": "Mars", "भौ": "Mars",
    # Mercury
    "ME": "Mercury", "MERCURY": "Mercury", "BUDHA": "Mercury", "BUDH": "Mercury", "BU": "Mercury", "MER": "Mercury", "MC": "Mercury",
    "बुध": "Mercury", "बु": "Mercury", "बुधः": "Mercury",
    # Jupiter
    "JU": "Jupiter", "JUPITER": "Jupiter", "GURU": "Jupiter", "BRIHASPATI": "Jupiter", "GU": "Jupiter", "BR": "Jupiter", "JUP": "Jupiter",
    "JP": "Jupiter", "GUR": "Jupiter", "BRIH": "Jupiter", "गुरु": "Jupiter", "गुरू": "Jupiter", "बृहस्पति": "Jupiter", "जीव": "Jupiter", "गु": "Jupiter", "बृ": "Jupiter", "जी": "Jupiter",
    # Venus
    "VE": "Venus", "VENUS": "Venus", "SHUKRA": "Venus", "SUKRA": "Venus", "SK": "Venus", "VEN": "Venus", "VN": "Venus", "SHU": "Venus",
    "SHUK": "Venus", "SUK": "Venus", "शुक्र": "Venus", "शु": "Venus", "भृगु": "Venus", "शुक्रः": "Venus",
    # Saturn
    "SA": "Saturn", "SATURN": "Saturn", "SHANI": "Saturn", "SANI": "Saturn", "SN": "Saturn", "SAT": "Saturn", "ST": "Saturn", "SHAN": "Saturn", "SAN": "Saturn",
    "शनि": "Saturn", "शनैश्चर": "Saturn", "मंद": "Saturn", "श": "Saturn", "शं": "Saturn",
    # Rahu
    "RA": "Rahu", "RAHU": "Rahu", "NORTH NODE": "Rahu", "NN": "Rahu", "RAH": "Rahu", "RH": "Rahu",
    "राहु": "Rahu", "तम": "Rahu", "रा": "Rahu", "सैंहिकेय": "Rahu",
    # Ketu
    "KE": "Ketu", "KETU": "Ketu", "SOUTH NODE": "Ketu", "SN_NODE": "Ketu", "KET": "Ketu", "KT": "Ketu",
    "केतु": "Ketu", "शिखी": "Ketu", "के": "Ketu", "ध्वज": "Ketu",
    # Ascendant / Lagna
    "ASC": "Ascendant", "ASCENDANT": "Ascendant", "LAGNA": "Ascendant", "LAG": "Ascendant", "AS": "Ascendant", "LA": "Ascendant", "LG": "Ascendant", "AC": "Ascendant",
    "लग्न": "Ascendant", "ल": "Ascendant", "तनु": "Ascendant",
    # Outer Planets / Sub-planets
    "UR": "Uranus", "URANUS": "Uranus", "HARSHAL": "Uranus", "हर्षल": "Uranus",
    "NE": "Neptune", "NEPTUNE": "Neptune", "VARUN": "Neptune", "वरुण": "Neptune",
    "PL": "Pluto", "PLUTO": "Pluto", "YAMA": "Pluto", "यम": "Pluto",
    "MANDI": "Mandi", "GULIKA": "Gulika", "GUL": "Gulika", "MAN": "Mandi", "गुलिक": "Gulika", "मांदि": "Mandi",
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

# 12 exact normalized [0, 1] x [0, 1] polygons for the North Indian Diamond Kundli grid.
# 4 center diamonds + 8 outer triangles perfectly partition the unit square without any overlap.
NORTH_INDIAN_POLYGONS: dict[int, list[tuple[float, float]]] = {
    1: [(0.5, 0.0), (0.25, 0.25), (0.5, 0.5), (0.75, 0.25)],         # House 1 (Top Center Diamond)
    2: [(0.0, 0.0), (0.5, 0.0), (0.25, 0.25)],                       # House 2 (Top Left Triangle)
    3: [(0.0, 0.0), (0.0, 0.5), (0.25, 0.25)],                       # House 3 (Left Top Triangle)
    4: [(0.0, 0.5), (0.25, 0.25), (0.5, 0.5), (0.25, 0.75)],         # House 4 (Left Center Diamond)
    5: [(0.0, 0.5), (0.0, 1.0), (0.25, 0.75)],                       # House 5 (Left Bottom Triangle)
    6: [(0.0, 1.0), (0.5, 1.0), (0.25, 0.75)],                       # House 6 (Bottom Left Triangle)
    7: [(0.5, 0.5), (0.25, 0.75), (0.5, 1.0), (0.75, 0.75)],         # House 7 (Bottom Center Diamond)
    8: [(0.5, 1.0), (1.0, 1.0), (0.75, 0.75)],                       # House 8 (Bottom Right Triangle)
    9: [(1.0, 0.5), (1.0, 1.0), (0.75, 0.75)],                       # House 9 (Right Bottom Triangle)
    10: [(0.5, 0.5), (0.75, 0.25), (1.0, 0.5), (0.75, 0.75)],       # House 10 (Right Center Diamond)
    11: [(1.0, 0.0), (1.0, 0.5), (0.75, 0.25)],                     # House 11 (Right Top Triangle)
    12: [(0.5, 0.0), (1.0, 0.0), (0.75, 0.25)],                     # House 12 (Top Right Triangle)
}

# Centroids of each house polygon for proximity-based fallback
NORTH_INDIAN_CENTROIDS: dict[int, tuple[float, float]] = {
    1: (0.5, 0.25),
    2: (0.25, 0.08333),
    3: (0.08333, 0.25),
    4: (0.25, 0.5),
    5: (0.08333, 0.75),
    6: (0.25, 0.91667),
    7: (0.5, 0.75),
    8: (0.75, 0.91667),
    9: (0.91667, 0.75),
    10: (0.75, 0.5),
    11: (0.91667, 0.25),
    12: (0.75, 0.08333),
}


def is_point_in_polygon(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    """Determine if a point (x, y) is inside a 2D polygon using the ray-casting algorithm."""
    inside = False
    n = len(poly)
    if n < 3:
        return False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def map_point_to_north_indian_house(u: float, v: float) -> int:
    """Map normalized coordinates (u, v) in [0, 1] x [0, 1] to the exact North Indian house (1-12)."""
    # Clamp u, v to [0.0, 1.0]
    cu = max(0.0, min(1.0, u))
    cv = max(0.0, min(1.0, v))

    # 1. Exact polygon test
    for h_idx, poly in NORTH_INDIAN_POLYGONS.items():
        if is_point_in_polygon(cu, cv, poly):
            return h_idx

    # 2. Centroid distance fallback if exactly on border or edge
    min_dist = float("inf")
    closest_h = 1
    for h_idx, (cx, cy) in NORTH_INDIAN_CENTROIDS.items():
        dist = ((cu - cx) ** 2 + (cv - cy) ** 2) ** 0.5
        if dist < min_dist:
            min_dist = dist
            closest_h = h_idx

    return closest_h


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
        # Match patterns like: 14°20'15", 14*20', 14:20:15, 14.333, 14deg20min, 14 20'
        cleaned = text.replace("*", "°").replace("‘", "'").replace("’", "'").replace("”", '"').replace("“", '"')
        dms_match = re.search(r"(\d{1,2})[°:\s](\d{1,2})[':\s]?(\d{1,2})?\"?", cleaned)
        if dms_match:
            deg = int(dms_match.group(1))
            minute = int(dms_match.group(2))
            sec = int(dms_match.group(3)) if dms_match.group(3) else 0
            if 0 <= deg <= 30 and 0 <= minute < 60 and 0 <= sec < 60:
                decimal = deg + (minute / 60.0) + (sec / 3600.0)
                dms_str = f"{deg:02d}°{minute:02d}'{sec:02d}\""
                return round(decimal, 4), dms_str

        # Decimal degree: e.g. 14.33
        dec_match = re.search(r"(\d{1,2}\.\d+)", cleaned)
        if dec_match:
            val = float(dec_match.group(1))
            if 0.0 <= val <= 30.0:
                deg_int = int(val)
                min_int = int((val - deg_int) * 60)
                sec_int = int(round(((val - deg_int) * 60 - min_int) * 60))
                return round(val, 4), f"{deg_int:02d}°{min_int:02d}'{sec_int:02d}\""

        # Standalone degrees like 15°
        single_match = re.search(r"(\d{1,2})[°]", cleaned)
        if single_match:
            deg = int(single_match.group(1))
            if 0 <= deg <= 30:
                return float(deg), f"{deg:02d}°00'00\""

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
            "अश्विनी", "भरणी", "कृत्तिका", "रोहिणी", "मृगशिरा", "आर्द्रा",
            "पुनर्वसु", "पुष्य", "अश्लेषा", "मघा", "पूर्वाफाल्गुनी", "उत्तराफाल्गुनी",
            "हस्त", "चित्रा", "स्वाति", "विशाखा", "अनुराधा", "ज्येष्ठा",
            "मूल", "पूर्वाषाढ़ा", "उत्तराषाढ़ा", "श्रवण", "धनिष्ठा",
            "शतभिषा", "पूर्वभाद्रपद", "उत्तरभाद्रपद", "रेवती"
        ]:
            if re.search(rf"\b{nak}\b", text, re.IGNORECASE):
                found_nak = nak
                break

        pada: int | None = None
        pada_match = re.search(r"(?:pada|p|चरण|प)[\s:-]?([1-4])", text, re.IGNORECASE)
        if pada_match:
            pada = int(pada_match.group(1))
        elif found_nak:
            # Check trailing single digit after nakshatra name like "Ashwini 2"
            trailing = re.search(rf"{found_nak}\s*([1-4])\b", text, re.IGNORECASE)
            if trailing:
                pada = int(trailing.group(1))

        return found_nak, pada

    def find_nearby_attributes(
        self, target_token: OCRToken, all_tokens: list[OCRToken], max_pixel_distance: float = 120.0
    ) -> tuple[float | None, str | None, str | None, int | None, bool, bool]:
        """Search surrounding tokens near a planet token for its degree, nakshatra, pada, and flags."""
        deg_val: float | None = None
        deg_dms: str | None = None
        nak_val: str | None = None
        pada_val: int | None = None
        is_rx: bool = False
        is_comb: bool = False

        # First check text inside target_token itself
        d_val, d_str = self.extract_degree(target_token.text)
        if d_val is not None:
            deg_val, deg_dms = d_val, d_str
        n_val, p_val = self.extract_nakshatra_pada(target_token.text)
        if n_val:
            nak_val = n_val
        if p_val:
            pada_val = p_val

        if any(r in target_token.text.upper() for r in ["(R)", "RET", "वक्र", "Rx"]):
            is_rx = True
        if any(c in target_token.text.upper() for c in ["(C)", "COM", "अस्त", "🔥"]):
            is_comb = True

        # Now search nearby spatial tokens
        if target_token.bbox:
            t_cx = target_token.bbox.x + (target_token.bbox.width / 2.0)
            t_cy = target_token.bbox.y + (target_token.bbox.height / 2.0)

            # Sort nearby tokens by distance
            nearby = []
            for tok in all_tokens:
                if tok is target_token:
                    continue
                if tok.bbox:
                    o_cx = tok.bbox.x + (tok.bbox.width / 2.0)
                    o_cy = tok.bbox.y + (tok.bbox.height / 2.0)
                    dist = ((t_cx - o_cx) ** 2 + (t_cy - o_cy) ** 2) ** 0.5
                    if dist <= max_pixel_distance:
                        nearby.append((dist, tok))

            nearby.sort(key=lambda x: x[0])

            for _, tok in nearby:
                txt = tok.text
                if deg_val is None:
                    d_val, d_str = self.extract_degree(txt)
                    if d_val is not None:
                        deg_val, deg_dms = d_val, d_str
                if nak_val is None or pada_val is None:
                    n_val, p_val = self.extract_nakshatra_pada(txt)
                    if n_val and nak_val is None:
                        nak_val = n_val
                    if p_val is not None and pada_val is None:
                        pada_val = p_val
                if pada_val is None:
                    p_match = re.search(r"(?:pada|p|चरण|प)[\s:-]?([1-4])", txt, re.IGNORECASE)
                    if p_match:
                        pada_val = int(p_match.group(1))
                if not is_rx and any(r in txt.upper() for r in ["(R)", "RET", "वक्र", "RX"]):
                    is_rx = True
                if not is_comb and any(c in txt.upper() for c in ["(C)", "COM", "अस्त"]):
                    is_comb = True

        return deg_val, deg_dms, nak_val, pada_val, is_rx, is_comb

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

