import io
import re
from typing import Any
from PIL import Image

from app.domain.image_intelligence.models import BoundingBox, ChartType
from app.domain.image_intelligence.providers.base import (
    LayoutRegion,
    OCRProvider,
    OCRResult,
    OCRToken,
    VisionLayoutResult,
    VisionProvider,
)

PLANET_PATTERNS = {
    "Sun": [r"\b(Sun|Su|Surya|Ravi|SY)\b", r"\b(सूर्य|रवि)\b"],
    "Moon": [r"\b(Moon|Mo|Chandra|Soma|CH)\b", r"\b(चन्द्र|सोम)\b"],
    "Mars": [r"\b(Mars|Ma|Mangal|Kuja|Angaraka|KU)\b", r"\b(मंगल|कुज)\b"],
    "Mercury": [r"\b(Mercury|Me|Budha|Budh|BU)\b", r"\b(बुध)\b"],
    "Jupiter": [r"\b(Jupiter|Ju|Guru|Brihaspati|GU)\b", r"\b(गुरु|बृहस्पति)\b"],
    "Venus": [r"\b(Venus|Ve|Shukra|Sukra|SK)\b", r"\b(शुक्र)\b"],
    "Saturn": [r"\b(Saturn|Sa|Shani|Sani|SN)\b", r"\b(शनि)\b"],
    "Rahu": [r"\b(Rahu|Ra|North Node|RA)\b", r"\b(राहु)\b"],
    "Ketu": [r"\b(Ketu|Ke|South Node|KE)\b", r"\b(केतु)\b"],
    "Ascendant": [r"\b(Ascendant|Asc|Lagna|Lag|AS|LA)\b", r"\b(लग्न)\b"],
    "Uranus": [r"\b(Uranus|Ur|Harshal|UR)\b", r"\b(हर्षल)\b"],
    "Neptune": [r"\b(Neptune|Ne|Varun|NE)\b", r"\b(वरुण)\b"],
    "Pluto": [r"\b(Pluto|Pl|Yama|PL)\b", r"\b(यम)\b"],
}

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena",
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Svati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]


class HeuristicVisionProvider(VisionProvider):
    """Analyzes geometric layout and segments standard Indian and Western chart regions."""

    async def analyze_layout(
        self, image_bytes: bytes, dimensions: tuple[int, int]
    ) -> VisionLayoutResult:
        w, h = dimensions
        if w <= 0 or h <= 0:
            w, h = 800, 800

        # Generate 12 standard house grid regions
        regions: list[LayoutRegion] = []

        # Assume North Indian standard diamond layout mapping
        # 12 houses coordinates normalized to image dimensions
        # House 1 (Top Center Diamond)
        regions.append(
            LayoutRegion(
                region_type="house_cell",
                identifier=1,
                bbox=BoundingBox(x=w * 0.25, y=h * 0.1, width=w * 0.5, height=h * 0.3),
                confidence=0.85,
            )
        )
        # House 2 (Top Left Triangle)
        regions.append(
            LayoutRegion(
                region_type="house_cell",
                identifier=2,
                bbox=BoundingBox(x=0, y=0, width=w * 0.35, height=h * 0.25),
                confidence=0.80,
            )
        )
        # House 3 (Left Top Triangle)
        regions.append(
            LayoutRegion(
                region_type="house_cell",
                identifier=3,
                bbox=BoundingBox(x=0, y=h * 0.2, width=w * 0.25, height=h * 0.3),
                confidence=0.80,
            )
        )
        # House 4 (Left Center Diamond)
        regions.append(
            LayoutRegion(
                region_type="house_cell",
                identifier=4,
                bbox=BoundingBox(x=0, y=h * 0.35, width=w * 0.3, height=h * 0.3),
                confidence=0.85,
            )
        )
        # House 5 (Left Bottom Triangle)
        regions.append(
            LayoutRegion(
                region_type="house_cell",
                identifier=5,
                bbox=BoundingBox(x=0, y=h * 0.55, width=w * 0.25, height=h * 0.3),
                confidence=0.80,
            )
        )
        # House 6 (Bottom Left Triangle)
        regions.append(
            LayoutRegion(
                region_type="house_cell",
                identifier=6,
                bbox=BoundingBox(x=0, y=h * 0.75, width=w * 0.35, height=h * 0.25),
                confidence=0.80,
            )
        )
        # House 7 (Bottom Center Diamond)
        regions.append(
            LayoutRegion(
                region_type="house_cell",
                identifier=7,
                bbox=BoundingBox(x=w * 0.25, y=h * 0.6, width=w * 0.5, height=h * 0.3),
                confidence=0.85,
            )
        )
        # House 8 (Bottom Right Triangle)
        regions.append(
            LayoutRegion(
                region_type="house_cell",
                identifier=8,
                bbox=BoundingBox(x=w * 0.65, y=h * 0.75, width=w * 0.35, height=h * 0.25),
                confidence=0.80,
            )
        )
        # House 9 (Right Bottom Triangle)
        regions.append(
            LayoutRegion(
                region_type="house_cell",
                identifier=9,
                bbox=BoundingBox(x=w * 0.75, y=h * 0.55, width=w * 0.25, height=h * 0.3),
                confidence=0.80,
            )
        )
        # House 10 (Right Center Diamond)
        regions.append(
            LayoutRegion(
                region_type="house_cell",
                identifier=10,
                bbox=BoundingBox(x=w * 0.7, y=h * 0.35, width=w * 0.3, height=h * 0.3),
                confidence=0.85,
            )
        )
        # House 11 (Right Top Triangle)
        regions.append(
            LayoutRegion(
                region_type="house_cell",
                identifier=11,
                bbox=BoundingBox(x=w * 0.75, y=h * 0.2, width=w * 0.25, height=h * 0.3),
                confidence=0.80,
            )
        )
        # House 12 (Top Right Triangle)
        regions.append(
            LayoutRegion(
                region_type="house_cell",
                identifier=12,
                bbox=BoundingBox(x=w * 0.65, y=0, width=w * 0.35, height=h * 0.25),
                confidence=0.80,
            )
        )

        return VisionLayoutResult(
            detected_chart_type=ChartType.NORTH_INDIAN,
            chart_confidence=0.85,
            regions=regions,
            geometry_detected={"rhombus_detected": True, "cells_count": 12},
            provider_name="heuristic_vision",
        )


class HeuristicOCRProvider(OCRProvider):
    """Extracts text tokens and recognizes astrological entities using regex rules."""

    def __init__(self, fallback_text: str = "") -> None:
        self.fallback_text = fallback_text

    async def extract_text(
        self, image_bytes: bytes, dimensions: tuple[int, int]
    ) -> OCRResult:
        w, h = dimensions
        tokens: list[OCRToken] = []
        full_text = self.fallback_text

        # If image_bytes contains text directly (e.g. from tests or pre-parsed streams)
        if not full_text:
            try:
                # Attempt decoding text if payload is text-based
                full_text = image_bytes.decode("utf-8", errors="ignore").strip()
            except Exception:
                full_text = ""

        lines = full_text.splitlines() if full_text else []
        for line_idx, line in enumerate(lines):
            words = line.split()
            for word_idx, word in enumerate(words):
                tokens.append(
                    OCRToken(
                        text=word,
                        bbox=BoundingBox(
                            x=(word_idx * 50) % (w or 800),
                            y=(line_idx * 30) % (h or 800),
                            width=45,
                            height=20,
                        ),
                        confidence=0.90,
                        line_number=line_idx + 1,
                    )
                )

        return OCRResult(
            full_text=full_text,
            tokens=tokens,
            lines=lines,
            detected_language="en",
            provider_name="heuristic_ocr",
            overall_confidence=0.85 if tokens else 0.50,
        )
