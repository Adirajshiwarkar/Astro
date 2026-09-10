from typing import Any
from app.domain.image_intelligence.models import (
    ExtractedPlanetPlacement,
    StructuredChartRepresentation,
)

# Standard Vedic Planetary Dignity Mappings (Sign Numbers 1-12)
EXALTATION_MAP = {
    "Sun": 1,        # Aries
    "Moon": 2,       # Taurus
    "Mars": 10,      # Capricorn
    "Mercury": 6,    # Virgo
    "Jupiter": 4,    # Cancer
    "Venus": 12,     # Pisces
    "Saturn": 7,     # Libra
    "Rahu": 2,       # Taurus / Gemini
    "Ketu": 8,       # Scorpio / Sagittarius
}

DEBILITATION_MAP = {
    "Sun": 7,        # Libra
    "Moon": 8,       # Scorpio
    "Mars": 4,       # Cancer
    "Mercury": 12,   # Pisces
    "Jupiter": 10,   # Capricorn
    "Venus": 6,      # Virgo
    "Saturn": 1,     # Aries
    "Rahu": 8,       # Scorpio
    "Ketu": 2,       # Taurus
}

OWN_SIGNS_MAP = {
    "Sun": [5],            # Leo
    "Moon": [4],           # Cancer
    "Mars": [1, 8],        # Aries, Scorpio
    "Mercury": [3, 6],     # Gemini, Virgo
    "Jupiter": [9, 12],    # Sagittarius, Pisces
    "Venus": [2, 7],       # Taurus, Libra
    "Saturn": [10, 11],    # Capricorn, Aquarius
}

FRIEND_SIGNS_MAP = {
    "Sun": [1, 4, 8, 9, 12],
    "Moon": [1, 3, 5, 6, 9, 12],
    "Mars": [4, 5, 9, 12],
    "Mercury": [2, 5, 7, 11],
    "Jupiter": [1, 4, 5, 8],
    "Venus": [3, 6, 10, 11],
    "Saturn": [2, 3, 6, 7],
}

ENEMY_SIGNS_MAP = {
    "Sun": [2, 6, 7, 10, 11],
    "Moon": [],
    "Mars": [3, 6],
    "Mercury": [4],
    "Jupiter": [3, 6, 2, 7],
    "Venus": [1, 4, 8],
    "Saturn": [1, 4, 5, 8],
}


class ChartReasoningSynthesizer:
    """Performs deep astrological reasoning, yoga detection, dignity assessment,

    and life domain scoring on parsed Kundli/astrological charts.
    """

    def synthesize(self, chart: StructuredChartRepresentation) -> dict[str, Any]:
        """Generate comprehensive astrological synthesis and reasoning metrics."""
        planets_by_name: dict[str, ExtractedPlanetPlacement] = {}
        for p in chart.planets:
            p_name = p.planet.value.title()
            planets_by_name[p_name] = p

        asc_sign_num = (
            chart.ascendant.sign_number.value
            if chart.ascendant and chart.ascendant.sign_number
            else (
                chart.houses[0].sign_number.value
                if chart.houses and chart.houses[0].sign_number
                else 1
            )
        )
        asc_sign_name = (
            chart.ascendant.sign.value
            if chart.ascendant and chart.ascendant.sign
            else "Aries"
        )

        # 1. Planetary Dignities & Strengths
        dignities: dict[str, dict[str, Any]] = {}
        for p_name, p_data in planets_by_name.items():
            sign_num = (
                p_data.sign_number.value
                if p_data.sign_number
                else None
            )
            house_num = p_data.house.value if p_data.house else 1
            is_rx = bool(p_data.is_retrograde and p_data.is_retrograde.value)
            is_comb = bool(p_data.is_combust and p_data.is_combust.value)

            status = "Neutral"
            score = 65
            if sign_num:
                if sign_num == EXALTATION_MAP.get(p_name):
                    status = "Exalted (Uchcha)"
                    score = 95
                elif sign_num == DEBILITATION_MAP.get(p_name):
                    status = "Debilitated (Neecha)"
                    score = 35
                elif sign_num in OWN_SIGNS_MAP.get(p_name, []):
                    status = "Own Sign (Swakshetra)"
                    score = 85
                elif sign_num in FRIEND_SIGNS_MAP.get(p_name, []):
                    status = "Friendly Sign (Mitra)"
                    score = 75
                elif sign_num in ENEMY_SIGNS_MAP.get(p_name, []):
                    status = "Enemy Sign (Shatru)"
                    score = 45

            if is_rx:
                score += 5
            if is_comb:
                score -= 15

            dignities[p_name] = {
                "planet": p_name,
                "status": status,
                "score": max(20, min(100, score)),
                "house": house_num,
                "sign": p_data.sign.value if p_data.sign else "Unknown",
                "is_retrograde": is_rx,
                "is_combust": is_comb,
            }

        # 2. Astrological Yogas Identification
        detected_yogas: list[dict[str, Any]] = []

        # Gajakesari Yoga: Jupiter in Kendra (1, 4, 7, 10) from Moon
        if "Jupiter" in planets_by_name and "Moon" in planets_by_name:
            jup_h = planets_by_name["Jupiter"].house.value if planets_by_name["Jupiter"].house else 1
            moon_h = planets_by_name["Moon"].house.value if planets_by_name["Moon"].house else 1
            dist = (jup_h - moon_h) % 12
            if dist in (0, 3, 6, 9):  # 1st, 4th, 7th, 10th
                detected_yogas.append({
                    "name": "Gaja Kesari Yoga",
                    "category": "Auspicious Auspice (Shubha)",
                    "planets": ["Jupiter", "Moon"],
                    "description": "Jupiter is in an angular house (Kendra) from the Moon, granting wisdom, leadership, enduring fame, and financial prosperity.",
                    "strength_factor": "Strong",
                })

        # Budhaditya Yoga: Sun and Mercury in the same house
        if "Sun" in planets_by_name and "Mercury" in planets_by_name:
            sun_h = planets_by_name["Sun"].house.value if planets_by_name["Sun"].house else 1
            merc_h = planets_by_name["Mercury"].house.value if planets_by_name["Mercury"].house else 1
            if sun_h == merc_h:
                detected_yogas.append({
                    "name": "Budhaditya Yoga",
                    "category": "Intellectual Mastery",
                    "planets": ["Sun", "Mercury"],
                    "description": f"Sun and Mercury conjunct in House {sun_h}, conferring high analytical intellect, executive communication, and administrative acumen.",
                    "strength_factor": "Very Strong" if not (planets_by_name["Mercury"].is_combust and planets_by_name["Mercury"].is_combust.value) else "Moderate",
                })

        # Chandra-Mangala Yoga: Moon and Mars conjunction
        if "Moon" in planets_by_name and "Mars" in planets_by_name:
            moon_h = planets_by_name["Moon"].house.value if planets_by_name["Moon"].house else 1
            mars_h = planets_by_name["Mars"].house.value if planets_by_name["Mars"].house else 1
            if moon_h == mars_h:
                detected_yogas.append({
                    "name": "Chandra-Mangala Yoga",
                    "category": "Wealth & Commercial Vigor",
                    "planets": ["Moon", "Mars"],
                    "description": f"Moon and Mars conjunct in House {moon_h}, producing commercial vitality, determination, and wealth-accumulating drive.",
                    "strength_factor": "Strong",
                })

        # Guru-Mangala Yoga: Jupiter and Mars conjunction or mutual aspect
        if "Jupiter" in planets_by_name and "Mars" in planets_by_name:
            jup_h = planets_by_name["Jupiter"].house.value if planets_by_name["Jupiter"].house else 1
            mars_h = planets_by_name["Mars"].house.value if planets_by_name["Mars"].house else 1
            if jup_h == mars_h or abs(jup_h - mars_h) == 6:
                detected_yogas.append({
                    "name": "Guru-Mangala Yoga",
                    "category": "Dharmic Authority",
                    "planets": ["Jupiter", "Mars"],
                    "description": "Jupiter and Mars in mutual alignment, energizing moral authority, technical mastery, and courageous decision-making.",
                    "strength_factor": "Strong",
                })

        # Kendra-Trikona Raja Yoga: Benefit planets in Kendra (1,4,7,10) or Trikona (1,5,9)
        kendra_houses = {1, 4, 7, 10}
        trikona_houses = {1, 5, 9}
        kendra_occupants = [p for p in chart.planets if p.house and p.house.value in kendra_houses]
        trikona_occupants = [p for p in chart.planets if p.house and p.house.value in trikona_houses]

        if len(kendra_occupants) >= 2 and len(trikona_occupants) >= 2:
            detected_yogas.append({
                "name": "Kendra-Trikona Sambandha Yoga",
                "category": "Raja Yoga (Status & Auspice)",
                "planets": [p.planet.value for p in kendra_occupants[:3]],
                "description": "Harmonious synergy between angular (Kendra) and trinal (Trikona) house energies establishes stability, high status, and auspicious progress.",
                "strength_factor": "High",
            })

        # 3. Life Domain Quantitative Scores
        career_score = 70
        finance_score = 72
        relationship_score = 68
        health_score = 75
        spiritual_score = 80

        # Adjust domain scores based on key house occupants
        house_occupants_map: dict[int, list[str]] = {h: [] for h in range(1, 13)}
        for p in chart.planets:
            if p.house and p.house.value:
                house_occupants_map[p.house.value].append(p.planet.value.title())

        # House 10 (Career)
        if any(p in house_occupants_map.get(10, []) for p in ["Sun", "Mars", "Jupiter"]):
            career_score += 15
        elif any(p in house_occupants_map.get(10, []) for p in ["Saturn", "Mercury"]):
            career_score += 10

        # House 2 & 11 (Wealth & Gains)
        if any(p in house_occupants_map.get(2, []) + house_occupants_map.get(11, []) for p in ["Jupiter", "Venus", "Mercury"]):
            finance_score += 16
        if any(p in house_occupants_map.get(2, []) + house_occupants_map.get(11, []) for p in ["Sun", "Moon"]):
            finance_score += 8

        # House 7 (Relationships)
        if "Venus" in house_occupants_map.get(7, []) or "Jupiter" in house_occupants_map.get(7, []):
            relationship_score += 14
        elif "Mars" in house_occupants_map.get(7, []) or "Saturn" in house_occupants_map.get(7, []):
            relationship_score -= 8

        # House 1 & 6 (Health)
        if "Sun" in house_occupants_map.get(1, []) or "Jupiter" in house_occupants_map.get(1, []):
            health_score += 12
        if "Mars" in house_occupants_map.get(6, []) or "Saturn" in house_occupants_map.get(6, []):
            health_score += 8  # Malefics in 6 destroy enemies/diseases

        # House 9 & 12 (Spiritual)
        if any(p in house_occupants_map.get(9, []) + house_occupants_map.get(12, []) for p in ["Jupiter", "Ketu", "Sun"]):
            spiritual_score += 15

        domain_scores = {
            "career": min(98, max(30, career_score)),
            "finance": min(98, max(30, finance_score)),
            "relationships": min(98, max(30, relationship_score)),
            "health": min(98, max(30, health_score)),
            "spirituality": min(98, max(30, spiritual_score)),
        }

        # 4. Strategic Astrological Insights
        insights: list[str] = []
        insights.append(f"Ascendant (Lagna) anchored in {asc_sign_name} creates a foundational temperament of vitality and purpose.")
        if detected_yogas:
            insights.append(f"Dominant Yoga: {detected_yogas[0]['name']} activates major potentials in {detected_yogas[0]['category'].lower()}.")
        if "Sun" in planets_by_name:
            sun_p = planets_by_name["Sun"]
            insights.append(f"Sun in {sun_p.sign.value if sun_p.sign else 'Lagna'} (House {sun_p.house.value if sun_p.house else 1}) channels executive drive.")
        if "Moon" in planets_by_name:
            moon_p = planets_by_name["Moon"]
            insights.append(f"Moon situated in {moon_p.sign.value if moon_p.sign else 'Rashi'} governs the emotional core and instinctual intelligence.")
        if chart.dasha and chart.dasha.current_mahadasha:
            insights.append(f"Current Mahadasha of {chart.dasha.current_mahadasha.value} shapes the present operational karmic cycle.")

        occupied_h_count = len([h for h in chart.houses if h.occupants])
        if occupied_h_count == 0 and chart.planets:
            occupied_h_count = len(set(p.house.value for p in chart.planets if p.house and p.house.value))

        return {
            "ascendant_sign": asc_sign_name,
            "ascendant_sign_number": asc_sign_num,
            "planetary_dignities": dignities,
            "detected_yogas": detected_yogas,
            "domain_scores": domain_scores,
            "insights": insights,
            "total_planets_analyzed": len(chart.planets),
            "total_occupied_houses": occupied_h_count,
        }
