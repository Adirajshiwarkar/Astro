from typing import Any

from app.domain.image_intelligence.models import (
    ExtractedPlanetPlacement,
    StructuredChartRepresentation,
)

VALID_NAKSHATRAS = {
    "ashwini", "bharani", "krittika", "rohini", "mrigashira", "ardra",
    "punarvasu", "pushya", "ashlesha", "magha", "purva phalguni", "uttara phalguni",
    "hasta", "chitra", "svati", "vishakha", "anuradha", "jyeshtha",
    "mula", "purva ashadha", "uttara ashadha", "shravana", "dhanishta",
    "shatabhisha", "purva bhadrapada", "uttara bhadrapada", "revati",
}

VALID_SIGNS = {
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
    "mesha", "vrishabha", "mithuna", "karka", "simha", "kanya",
    "tula", "vrischika", "dhanu", "makara", "kumbha", "meena",
}


class ChartExtractionValidator:
    """Validates extracted astrological chart representations for astronomical consistency

    and anomalies without hallucinating missing data.
    """

    def validate(self, chart: StructuredChartRepresentation) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Check Ascendant
        if not chart.ascendant:
            warnings.append("Ascendant (Lagna) was not explicitly detected.")
        else:
            if chart.ascendant.sign_number and not (1 <= chart.ascendant.sign_number.value <= 12):
                errors.append(f"Invalid Ascendant sign number: {chart.ascendant.sign_number.value}")
            if chart.ascendant.degree and not (0.0 <= chart.ascendant.degree.value < 30.0):
                errors.append(f"Ascendant degree {chart.ascendant.degree.value} out of range [0.0, 30.0).")

        # 2. Check Planets
        seen_planets: set[str] = set()
        for p in chart.planets:
            pname = p.planet.value
            if pname in seen_planets:
                warnings.append(f"Duplicate planet placement detected for {pname}.")
            seen_planets.add(pname)

            if p.sign and p.sign.value.lower() not in VALID_SIGNS:
                warnings.append(f"Unrecognized sign '{p.sign.value}' for planet {pname}.")

            if p.sign_number and not (1 <= p.sign_number.value <= 12):
                errors.append(f"Invalid sign number {p.sign_number.value} for planet {pname}.")

            if p.house and not (1 <= p.house.value <= 12):
                errors.append(f"Invalid house number {p.house.value} for planet {pname}.")

            if p.degree and not (0.0 <= p.degree.value < 30.0):
                errors.append(f"Invalid degree {p.degree.value} for planet {pname} (must be in [0.0, 30.0)).")

            if p.nakshatra and p.nakshatra.value.lower() not in VALID_NAKSHATRAS:
                warnings.append(f"Unrecognized nakshatra '{p.nakshatra.value}' for planet {pname}.")

            if p.pada and not (1 <= p.pada.value <= 4):
                errors.append(f"Invalid nakshatra pada {p.pada.value} for planet {pname} (must be 1-4).")

        # 3. Check Houses
        if len(chart.houses) != 12:
            warnings.append(f"Expected 12 houses, but found {len(chart.houses)}.")

        for h in chart.houses:
            if not (1 <= h.house_number.value <= 12):
                errors.append(f"Invalid house number {h.house_number.value}.")
            if h.sign_number and not (1 <= h.sign_number.value <= 12):
                errors.append(f"Invalid house sign number {h.sign_number.value} for house {h.house_number.value}.")
            if h.cusp_degree and not (0.0 <= h.cusp_degree.value < 360.0):
                errors.append(f"House cusp degree {h.cusp_degree.value} out of range [0.0, 360.0).")

        is_valid = len(errors) == 0

        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "total_planets_extracted": len(chart.planets),
            "total_houses_extracted": len(chart.houses),
            "has_ascendant": chart.ascendant is not None,
            "has_dasha": chart.dasha is not None,
        }
