from typing import Any

from app.domain.astrology.models import WesternChart
from app.domain.canonical.models import CanonicalChartRepresentation
from app.domain.numerology.models import NumerologyProfile
from app.domain.signals.models import FactorPolarity, SignalDomain, SignalFactor, SourceSystem
from app.domain.vedic.models import VedicChart


def extract_western_signals(western: WesternChart) -> dict[SignalDomain, list[SignalFactor]]:
    """Extract domain factors from Western chart placements, aspects, and houses."""
    factors: dict[SignalDomain, list[SignalFactor]] = {d: [] for d in SignalDomain}

    # Analyze placements
    for p in western.placements:
        name = p.name.lower()
        house = p.house

        # Career: 10th House
        if house == 10:
            polarity = FactorPolarity.POSITIVE if name in ("sun", "jupiter", "mars", "mercury") else FactorPolarity.NEUTRAL
            factors[SignalDomain.CAREER].append(
                SignalFactor(
                    factor_id=f"WEST-PL-{p.name}-H10",
                    name=f"Western {p.name} in 10th House",
                    source_system=SourceSystem.WESTERN,
                    weight=0.90 if name in ("sun", "jupiter") else 0.75,
                    polarity=polarity,
                    description=f"Planet {p.name} situated in 10th house of career and public standing",
                    timeframe="natal",
                    metadata={"planet": p.name, "house": 10, "sign": p.sign},
                )
            )

        # Finance: 2nd and 8th House
        if house in (2, 8):
            polarity = FactorPolarity.POSITIVE if name in ("jupiter", "venus", "sun") else (FactorPolarity.NEGATIVE if p.is_retrograde and name == "saturn" else FactorPolarity.NEUTRAL)
            factors[SignalDomain.FINANCE].append(
                SignalFactor(
                    factor_id=f"WEST-PL-{p.name}-H{house}",
                    name=f"Western {p.name} in {house}th House",
                    source_system=SourceSystem.WESTERN,
                    weight=0.85 if name in ("jupiter", "venus") else 0.70,
                    polarity=polarity,
                    description=f"Planet {p.name} situated in house {house} governing resources",
                    timeframe="natal",
                    metadata={"planet": p.name, "house": house},
                )
            )

        # Relationship & Marriage: 7th House
        if house == 7:
            polarity = FactorPolarity.POSITIVE if name in ("venus", "jupiter", "moon") else (FactorPolarity.NEGATIVE if name in ("saturn", "mars") and p.is_retrograde else FactorPolarity.NEUTRAL)
            factors[SignalDomain.RELATIONSHIP].append(
                SignalFactor(
                    factor_id=f"WEST-PL-{p.name}-H7-REL",
                    name=f"Western {p.name} in 7th House",
                    source_system=SourceSystem.WESTERN,
                    weight=0.90 if name in ("venus", "moon") else 0.75,
                    polarity=polarity,
                    description=f"Planet {p.name} in 7th house of partnerships",
                    timeframe="natal",
                )
            )
            factors[SignalDomain.MARRIAGE].append(
                SignalFactor(
                    factor_id=f"WEST-PL-{p.name}-H7-MAR",
                    name=f"Western {p.name} in 7th House (Marriage)",
                    source_system=SourceSystem.WESTERN,
                    weight=0.85 if name in ("venus", "jupiter") else 0.70,
                    polarity=polarity,
                    description=f"7th house placement {p.name} influencing marriage commitments",
                    timeframe="natal",
                )
            )

        # Education: 3rd and 9th House
        if house in (3, 9):
            factors[SignalDomain.EDUCATION].append(
                SignalFactor(
                    factor_id=f"WEST-PL-{p.name}-H{house}",
                    name=f"Western {p.name} in {house}th House",
                    source_system=SourceSystem.WESTERN,
                    weight=0.85 if name in ("mercury", "jupiter") else 0.65,
                    polarity=FactorPolarity.POSITIVE,
                    description=f"Planet {p.name} in educational axis house {house}",
                    timeframe="natal",
                )
            )

        # Travel: 3rd and 9th House
        if house in (3, 9) or p.sign in ("Gemini", "Sagittarius", "Pisces"):
            factors[SignalDomain.TRAVEL].append(
                SignalFactor(
                    factor_id=f"WEST-TRV-{p.name}",
                    name=f"Western {p.name} in {p.sign}/H{house}",
                    source_system=SourceSystem.WESTERN,
                    weight=0.75 if house == 9 else 0.60,
                    polarity=FactorPolarity.POSITIVE,
                    description=f"Planetary placement in travel sector/mutable sign",
                    timeframe="natal",
                )
            )

        # Family & Relocation: 4th House
        if house == 4:
            factors[SignalDomain.FAMILY].append(
                SignalFactor(
                    factor_id=f"WEST-FAM-{p.name}",
                    name=f"Western {p.name} in 4th House",
                    source_system=SourceSystem.WESTERN,
                    weight=0.80,
                    polarity=FactorPolarity.POSITIVE if name in ("moon", "venus", "jupiter") else FactorPolarity.NEUTRAL,
                    description="4th house placement governing family and domestic life",
                    timeframe="natal",
                )
            )
            factors[SignalDomain.RELOCATION].append(
                SignalFactor(
                    factor_id=f"WEST-RELOC-{p.name}",
                    name=f"Western {p.name} in 4th House (Relocation)",
                    source_system=SourceSystem.WESTERN,
                    weight=0.70,
                    polarity=FactorPolarity.POSITIVE if name in ("uranus", "mars") else FactorPolarity.NEUTRAL,
                    description="4th house dynamism affecting domestic residence",
                    timeframe="natal",
                )
            )

        # Personal Development: 1st House
        if house == 1:
            factors[SignalDomain.PERSONAL_DEVELOPMENT].append(
                SignalFactor(
                    factor_id=f"WEST-SELF-{p.name}",
                    name=f"Western {p.name} in 1st House",
                    source_system=SourceSystem.WESTERN,
                    weight=0.90 if name in ("sun", "jupiter") else 0.75,
                    polarity=FactorPolarity.POSITIVE,
                    description="1st house placement governing personal vitality and self-evolution",
                    timeframe="natal",
                )
            )

    # Analyze aspects
    for asp in western.aspects:
        p1, p2 = asp.point1.lower(), asp.point2.lower()
        pair = {p1, p2}
        asp_type = asp.aspect_type.lower()
        is_harmonious = asp_type in ("trine", "sextile", "conjunction")

        if {"sun", "jupiter"}.issubset(pair) or {"sun", "saturn"}.issubset(pair):
            polarity = FactorPolarity.POSITIVE if is_harmonious else FactorPolarity.NEGATIVE
            factors[SignalDomain.CAREER].append(
                SignalFactor(
                    factor_id=f"WEST-ASP-{asp.point1}-{asp.point2}",
                    name=f"Western {asp.point1} {asp.aspect_type} {asp.point2}",
                    source_system=SourceSystem.WESTERN,
                    weight=round(asp.strength * 0.85, 2),
                    polarity=polarity,
                    description=f"{asp.aspect_type.capitalize()} aspect influencing career drive",
                    timeframe="natal",
                )
            )

        if {"venus", "jupiter"}.issubset(pair):
            factors[SignalDomain.FINANCE].append(
                SignalFactor(
                    factor_id=f"WEST-ASP-{asp.point1}-{asp.point2}-FIN",
                    name=f"Western {asp.point1} {asp.aspect_type} {asp.point2}",
                    source_system=SourceSystem.WESTERN,
                    weight=round(asp.strength * 0.90, 2),
                    polarity=FactorPolarity.POSITIVE if is_harmonious else FactorPolarity.NEGATIVE,
                    description="Benefic aspect influencing wealth expansion",
                    timeframe="natal",
                )
            )

        if {"venus", "mars"}.issubset(pair) or {"venus", "moon"}.issubset(pair):
            factors[SignalDomain.RELATIONSHIP].append(
                SignalFactor(
                    factor_id=f"WEST-ASP-{asp.point1}-{asp.point2}-REL",
                    name=f"Western {asp.point1} {asp.aspect_type} {asp.point2}",
                    source_system=SourceSystem.WESTERN,
                    weight=round(asp.strength * 0.85, 2),
                    polarity=FactorPolarity.POSITIVE if is_harmonious else FactorPolarity.NEGATIVE,
                    description="Relational polarity aspect",
                    timeframe="natal",
                )
            )

    return factors


def extract_vedic_signals(vedic: VedicChart) -> dict[SignalDomain, list[SignalFactor]]:
    """Extract domain factors from Vedic chart grahas, bhavas, drishti, and dashas."""
    factors: dict[SignalDomain, list[SignalFactor]] = {d: [] for d in SignalDomain}

    for g in vedic.grahas:
        v_name = g.vedic_name
        bhava = g.bhava

        # Career: 10th Bhava (Karma)
        if bhava == 10:
            polarity = FactorPolarity.POSITIVE if v_name in ("Surya", "Guru", "Budha", "Mangala") else FactorPolarity.NEUTRAL
            factors[SignalDomain.CAREER].append(
                SignalFactor(
                    factor_id=f"VEDIC-GRAHA-{v_name}-B10",
                    name=f"Vedic {v_name} in 10th Bhava (Karma Sthana)",
                    source_system=SourceSystem.VEDIC,
                    weight=0.92 if v_name in ("Surya", "Guru") else 0.78,
                    polarity=polarity,
                    description=f"Graha {v_name} placed in 10th Bhava of profession and status",
                    timeframe="natal",
                    metadata={"graha": v_name, "bhava": 10, "rashi": g.rashi},
                )
            )
            factors[SignalDomain.BUSINESS].append(
                SignalFactor(
                    factor_id=f"VEDIC-BIZ-{v_name}-B10",
                    name=f"Vedic {v_name} in 10th Bhava (Enterprise)",
                    source_system=SourceSystem.VEDIC,
                    weight=0.85,
                    polarity=polarity,
                    description="10th bhava professional enterprise placement",
                    timeframe="natal",
                )
            )

        # Finance: 2nd (Dhana) and 11th (Labha/Gains) Bhavas
        if bhava in (2, 11):
            polarity = FactorPolarity.POSITIVE if v_name in ("Guru", "Shukra", "Budha", "Chandra") else FactorPolarity.NEUTRAL
            factors[SignalDomain.FINANCE].append(
                SignalFactor(
                    factor_id=f"VEDIC-GRAHA-{v_name}-B{bhava}",
                    name=f"Vedic {v_name} in {bhava}th Bhava ({'Dhana' if bhava==2 else 'Labha'})",
                    source_system=SourceSystem.VEDIC,
                    weight=0.90 if v_name in ("Guru", "Shukra") else 0.75,
                    polarity=polarity,
                    description=f"Graha {v_name} in wealth/gains bhava {bhava}",
                    timeframe="natal",
                )
            )

        # Relationship & Marriage: 7th Bhava (Yuvati Sthana)
        if bhava == 7:
            polarity = FactorPolarity.POSITIVE if v_name in ("Shukra", "Guru", "Chandra") else (FactorPolarity.NEGATIVE if v_name in ("Mangala", "Shani", "Rahu") and g.is_retrograde else FactorPolarity.NEUTRAL)
            factors[SignalDomain.RELATIONSHIP].append(
                SignalFactor(
                    factor_id=f"VEDIC-GRAHA-{v_name}-B7-REL",
                    name=f"Vedic {v_name} in 7th Bhava (Kalathra)",
                    source_system=SourceSystem.VEDIC,
                    weight=0.90,
                    polarity=polarity,
                    description=f"Graha {v_name} in 7th bhava of partnership",
                    timeframe="natal",
                )
            )
            factors[SignalDomain.MARRIAGE].append(
                SignalFactor(
                    factor_id=f"VEDIC-GRAHA-{v_name}-B7-MAR",
                    name=f"Vedic {v_name} in 7th Bhava (Vivaha)",
                    source_system=SourceSystem.VEDIC,
                    weight=0.88,
                    polarity=polarity,
                    description=f"Graha {v_name} in 7th bhava influencing marriage",
                    timeframe="natal",
                )
            )

        # Education: 4th (Vidya) & 5th (Buddhi) Bhavas
        if bhava in (4, 5):
            factors[SignalDomain.EDUCATION].append(
                SignalFactor(
                    factor_id=f"VEDIC-EDU-{v_name}-B{bhava}",
                    name=f"Vedic {v_name} in {bhava}th Bhava",
                    source_system=SourceSystem.VEDIC,
                    weight=0.88 if v_name in ("Budha", "Guru") else 0.70,
                    polarity=FactorPolarity.POSITIVE,
                    description=f"Graha in knowledge bhava {bhava}",
                    timeframe="natal",
                )
            )

        # Travel: 3rd, 9th, 12th Bhavas
        if bhava in (3, 9, 12):
            factors[SignalDomain.TRAVEL].append(
                SignalFactor(
                    factor_id=f"VEDIC-TRV-{v_name}-B{bhava}",
                    name=f"Vedic {v_name} in {bhava}th Bhava (Travel/Foreign)",
                    source_system=SourceSystem.VEDIC,
                    weight=0.80 if bhava in (9, 12) else 0.65,
                    polarity=FactorPolarity.POSITIVE,
                    description=f"Placement in journey/foreign bhava {bhava}",
                    timeframe="natal",
                )
            )
            if bhava == 12:
                factors[SignalDomain.RELOCATION].append(
                    SignalFactor(
                        factor_id=f"VEDIC-RELOC-{v_name}-B12",
                        name=f"Vedic {v_name} in 12th Bhava (Foreign Residency)",
                        source_system=SourceSystem.VEDIC,
                        weight=0.78,
                        polarity=FactorPolarity.POSITIVE,
                        description="12th bhava foreign relocation indicator",
                        timeframe="natal",
                    )
                )

        # Family: 2nd & 4th Bhavas
        if bhava in (2, 4):
            factors[SignalDomain.FAMILY].append(
                SignalFactor(
                    factor_id=f"VEDIC-FAM-{v_name}-B{bhava}",
                    name=f"Vedic {v_name} in {bhava}th Bhava ({'Kutumba' if bhava==2 else 'Matru'})",
                    source_system=SourceSystem.VEDIC,
                    weight=0.80,
                    polarity=FactorPolarity.POSITIVE if v_name in ("Chandra", "Guru") else FactorPolarity.NEUTRAL,
                    description="Placement governing family lineage and domestic peace",
                    timeframe="natal",
                )
            )

        # Personal Development: 1st Bhava (Tanu / Lagna)
        if bhava == 1:
            factors[SignalDomain.PERSONAL_DEVELOPMENT].append(
                SignalFactor(
                    factor_id=f"VEDIC-SELF-{v_name}-B1",
                    name=f"Vedic {v_name} in Lagna (1st Bhava)",
                    source_system=SourceSystem.VEDIC,
                    weight=0.92,
                    polarity=FactorPolarity.POSITIVE,
                    description="Lagna placement governing character, health, and self-realization",
                    timeframe="natal",
                )
            )

    return factors


def extract_numerology_signals(num_profile: NumerologyProfile) -> dict[SignalDomain, list[SignalFactor]]:
    """Extract domain factors from Numerology core numbers and personal cycles."""
    factors: dict[SignalDomain, list[SignalFactor]] = {d: [] for d in SignalDomain}

    lp = num_profile.life_path.calculated_value
    py = num_profile.personal_year.calculated_value if num_profile.personal_year else None
    su = num_profile.soul_urge.calculated_value

    # Career: Life Path 1, 8; Personal Year 1, 8
    if lp in (1, 8):
        factors[SignalDomain.CAREER].append(
            SignalFactor(
                factor_id=f"NUM-LP-{lp}-CAR",
                name=f"Numerology Life Path {lp} (Leadership/Achievement)",
                source_system=SourceSystem.NUMEROLOGY,
                weight=0.85,
                polarity=FactorPolarity.POSITIVE,
                description=f"Life Path {lp} emphasizes executive authority, career drive, and tangible manifestation",
                timeframe="natal",
            )
        )
        factors[SignalDomain.BUSINESS].append(
            SignalFactor(
                factor_id=f"NUM-LP-{lp}-BIZ",
                name=f"Numerology Life Path {lp} (Enterprise)",
                source_system=SourceSystem.NUMEROLOGY,
                weight=0.85,
                polarity=FactorPolarity.POSITIVE,
                description="Life path driving commercial ventures and business autonomy",
                timeframe="natal",
            )
        )

    if py in (1, 8):
        factors[SignalDomain.CAREER].append(
            SignalFactor(
                factor_id=f"NUM-PY-{py}-CAR",
                name=f"Personal Year {py} ({'New Cycle' if py==1 else 'Harvest/Executive Expansion'})",
                source_system=SourceSystem.NUMEROLOGY,
                weight=0.90,
                polarity=FactorPolarity.POSITIVE,
                description=f"Personal Year {py} creates strong professional acceleration",
                timeframe=f"Personal Year {py}",
            )
        )

    # Finance: Life Path 8, 4; Personal Year 8
    if lp in (8, 4):
        factors[SignalDomain.FINANCE].append(
            SignalFactor(
                factor_id=f"NUM-LP-{lp}-FIN",
                name=f"Numerology Life Path {lp} (Financial Foundations)",
                source_system=SourceSystem.NUMEROLOGY,
                weight=0.82,
                polarity=FactorPolarity.POSITIVE,
                description=f"Life path {lp} provides systematic wealth building acumen",
                timeframe="natal",
            )
        )
    if py == 8:
        factors[SignalDomain.FINANCE].append(
            SignalFactor(
                factor_id="NUM-PY-8-FIN",
                name="Personal Year 8 (Financial Manifestation)",
                source_system=SourceSystem.NUMEROLOGY,
                weight=0.92,
                polarity=FactorPolarity.POSITIVE,
                description="Personal Year 8 represents peak financial empowerment and resource consolidation",
                timeframe="Personal Year 8",
            )
        )

    # Relationship & Marriage: Life Path 2, 6; Soul Urge 2, 6; Personal Year 2, 6
    if lp in (2, 6) or su in (2, 6):
        factors[SignalDomain.RELATIONSHIP].append(
            SignalFactor(
                factor_id=f"NUM-REL-HARMONY-{lp if lp in (2,6) else su}",
                name=f"Numerology Harmony Cycle ({lp if lp in (2,6) else su})",
                source_system=SourceSystem.NUMEROLOGY,
                weight=0.80,
                polarity=FactorPolarity.POSITIVE,
                description="Vibrational emphasis on cooperative relationships and emotional harmony",
                timeframe="natal",
            )
        )
    if py in (2, 6):
        factors[SignalDomain.RELATIONSHIP].append(
            SignalFactor(
                factor_id=f"NUM-PY-{py}-REL",
                name=f"Personal Year {py} ({'Partnership' if py==2 else 'Domestic Responsibility'})",
                source_system=SourceSystem.NUMEROLOGY,
                weight=0.88,
                polarity=FactorPolarity.POSITIVE,
                description=f"Personal Year {py} prioritizes interpersonal bonds",
                timeframe=f"Personal Year {py}",
            )
        )
        if py == 6:
            factors[SignalDomain.MARRIAGE].append(
                SignalFactor(
                    factor_id="NUM-PY-6-MAR",
                    name="Personal Year 6 (Marriage & Domestic Commitment)",
                    source_system=SourceSystem.NUMEROLOGY,
                    weight=0.90,
                    polarity=FactorPolarity.POSITIVE,
                    description="Personal Year 6 is the primary cycle for solemn domestic commitments and marriage",
                    timeframe="Personal Year 6",
                )
            )
            factors[SignalDomain.FAMILY].append(
                SignalFactor(
                    factor_id="NUM-PY-6-FAM",
                    name="Personal Year 6 (Family Duty)",
                    source_system=SourceSystem.NUMEROLOGY,
                    weight=0.88,
                    polarity=FactorPolarity.POSITIVE,
                    description="Family duty and domestic harmony",
                    timeframe="Personal Year 6",
                )
            )

    # Education & Personal Development: Life Path 7; Personal Year 7
    if lp == 7 or py == 7:
        factors[SignalDomain.EDUCATION].append(
            SignalFactor(
                factor_id="NUM-7-EDU",
                name="Numerology 7 Analytical Learning",
                source_system=SourceSystem.NUMEROLOGY,
                weight=0.85,
                polarity=FactorPolarity.POSITIVE,
                description="Number 7 stimulates intellectual mastery, research, and specialized study",
                timeframe="cycle",
            )
        )
        factors[SignalDomain.PERSONAL_DEVELOPMENT].append(
            SignalFactor(
                factor_id="NUM-7-SELF",
                name="Numerology 7 Inner Evolution",
                source_system=SourceSystem.NUMEROLOGY,
                weight=0.92,
                polarity=FactorPolarity.POSITIVE,
                description="Number 7 focuses on spiritual awakening, self-inquiry, and consciousness expansion",
                timeframe="cycle",
            )
        )

    # Travel & Relocation: Life Path 5; Personal Year 5
    if lp == 5 or py == 5:
        factors[SignalDomain.TRAVEL].append(
            SignalFactor(
                factor_id="NUM-5-TRV",
                name="Numerology 5 Mobility & Freedom",
                source_system=SourceSystem.NUMEROLOGY,
                weight=0.88,
                polarity=FactorPolarity.POSITIVE,
                description="Number 5 indicates dynamic expansion, travel, and adventure",
                timeframe="cycle",
            )
        )
        factors[SignalDomain.RELOCATION].append(
            SignalFactor(
                factor_id="NUM-5-RELOC",
                name="Numerology 5 Transitional Relocation",
                source_system=SourceSystem.NUMEROLOGY,
                weight=0.80,
                polarity=FactorPolarity.POSITIVE,
                description="Number 5 indicates changes of residence, location, and environment",
                timeframe="cycle",
            )
        )

    return factors


def extract_canonical_signals(canonical: CanonicalChartRepresentation) -> dict[SignalDomain, list[SignalFactor]]:
    """Extract domain factors directly from unified CanonicalChartRepresentation."""
    factors: dict[SignalDomain, list[SignalFactor]] = {d: [] for d in SignalDomain}

    # Planets
    for p_name, p in canonical.planets.items():
        house = p.house.value if p.house else None
        sign = p.sign.value if p.sign else "Aries"
        p_name_clean = p_name.lower()

        if house == 10:
            factors[SignalDomain.CAREER].append(
                SignalFactor(
                    factor_id=f"CANON-PL-{p_name}-H10",
                    name=f"Canonical {p_name} in 10th House",
                    source_system=SourceSystem.CROSS_SYSTEM_CORRELATED,
                    weight=0.88,
                    polarity=FactorPolarity.POSITIVE,
                    description=f"{p_name} positioned in house 10 of career",
                    timeframe="natal",
                )
            )

        if house in (2, 11):
            factors[SignalDomain.FINANCE].append(
                SignalFactor(
                    factor_id=f"CANON-PL-{p_name}-H{house}",
                    name=f"Canonical {p_name} in {house}th House",
                    source_system=SourceSystem.CROSS_SYSTEM_CORRELATED,
                    weight=0.85,
                    polarity=FactorPolarity.POSITIVE,
                    description=f"{p_name} positioned in wealth house {house}",
                    timeframe="natal",
                )
            )

        if house == 7:
            factors[SignalDomain.RELATIONSHIP].append(
                SignalFactor(
                    factor_id=f"CANON-PL-{p_name}-H7",
                    name=f"Canonical {p_name} in 7th House",
                    source_system=SourceSystem.CROSS_SYSTEM_CORRELATED,
                    weight=0.88,
                    polarity=FactorPolarity.POSITIVE,
                    description=f"{p_name} in partnership house 7",
                    timeframe="natal",
                )
            )

    return factors
