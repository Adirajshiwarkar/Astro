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


NAVAGRAHAS = {
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"
}


class ChartExtractionValidator:
    """Validates extracted astrological chart representations for astronomical consistency,

    Navagraha completeness, nodal axis symmetry, and anomalies without hallucinating missing data.
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
        planets_by_name: dict[str, ExtractedPlanetPlacement] = {}

        for p in chart.planets:
            pname = p.planet.value
            planets_by_name[pname] = p

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

        # 4. Navagrahas Completeness
        found_navagrahas = [p for p in seen_planets if p in NAVAGRAHAS]
        navagrahas_count = len(found_navagrahas)
        completeness_score = round((navagrahas_count / 9.0) * 100)

        missing_navagrahas = list(NAVAGRAHAS - set(found_navagrahas))
        if missing_navagrahas:
            warnings.append(f"Missing classical planets in extraction: {', '.join(sorted(missing_navagrahas))}.")

        # 5. Astronomical Rahu-Ketu 180° Opposite Axis Check
        is_rahu_ketu_axis_valid = None
        if "Rahu" in planets_by_name and "Ketu" in planets_by_name:
            rahu_h = planets_by_name["Rahu"].house.value if planets_by_name["Rahu"].house else None
            ketu_h = planets_by_name["Ketu"].house.value if planets_by_name["Ketu"].house else None
            if rahu_h and ketu_h:
                diff = abs(rahu_h - ketu_h)
                is_rahu_ketu_axis_valid = (diff == 6)
                if not is_rahu_ketu_axis_valid:
                    warnings.append(
                        f"Astronomical Node Anomaly: Rahu (House {rahu_h}) and Ketu (House {ketu_h}) "
                        f"are not in the classical 7-house 180° opposite axis."
                    )

        is_valid = len(errors) == 0

        # 6. Realistic Status Label and Confidence Adjustment
        if is_valid:
            if completeness_score >= 85 and is_rahu_ketu_axis_valid is not False:
                status_label = "Astrologically Validated"
            elif completeness_score >= 40:
                status_label = f"Partial Extraction ({navagrahas_count}/9 Navagrahas)"
            else:
                status_label = f"Incomplete Extraction ({navagrahas_count}/9 Navagrahas)"
        else:
            status_label = "Validation Anomalies Detected"

        occupied_houses_count = len([h for h in chart.houses if h.occupants])

        # Adjust overall chart confidence based on completeness and errors
        calc_confidence = min(0.98, max(0.35, (
            (completeness_score * 0.5) +
            (45.0 if is_valid else 10.0) +
            (5.0 if is_rahu_ketu_axis_valid else 0.0)
        ) / 100.0))

        chart.overall_confidence = round(calc_confidence, 2)

        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "status_label": status_label,
            "navagrahas_count": navagrahas_count,
            "navagrahas_total": 9,
            "completeness_score": completeness_score,
            "missing_navagrahas": sorted(missing_navagrahas),
            "is_rahu_ketu_axis_valid": is_rahu_ketu_axis_valid,
            "total_planets_extracted": len(chart.planets),
            "total_houses_extracted": len(chart.houses),
            "occupied_houses_count": occupied_houses_count,
            "has_ascendant": chart.ascendant is not None,
            "has_dasha": chart.dasha is not None,
        }
