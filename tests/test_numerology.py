import datetime

import pytest

from app.domain.numerology.config import NumerologyConfig, NumerologySystem
from app.domain.numerology.engine import PYTHAGOREAN_VALUES, NumerologyEngine
from app.domain.numerology.models import (
    NumerologyCalculationResult,
    NumerologyProfile,
)


def test_pythagorean_table_completeness() -> None:
    """Verify that all 26 uppercase English letters are mapped to 1-9."""
    assert len(PYTHAGOREAN_VALUES) == 26
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        assert c in PYTHAGOREAN_VALUES
        assert 1 <= PYTHAGOREAN_VALUES[c] <= 9

    # Spot checks
    assert PYTHAGOREAN_VALUES["A"] == 1
    assert PYTHAGOREAN_VALUES["I"] == 9
    assert PYTHAGOREAN_VALUES["J"] == 1
    assert PYTHAGOREAN_VALUES["R"] == 9
    assert PYTHAGOREAN_VALUES["S"] == 1
    assert PYTHAGOREAN_VALUES["Z"] == 8


def test_life_path_standard_calculation() -> None:
    engine = NumerologyEngine()
    # October 12, 1990
    # Month: 10 -> 1 + 0 = 1
    # Day: 12 -> 1 + 2 = 3
    # Year: 1990 -> 1 + 9 + 9 + 0 = 19 -> 1 + 9 = 10 -> 1 + 0 = 1
    # Sum: 1 + 3 + 1 = 5
    dob = datetime.date(1990, 10, 12)
    res = engine.calculate_life_path(dob)

    assert isinstance(res, NumerologyCalculationResult)
    assert res.calculated_value == 5
    assert "Pythagorean Numerology System" in res.methodology
    assert res.source_input == "1990-10-12"
    assert len(res.calculation_steps) == 4
    assert res.engine_version == "1.0.0"


def test_life_path_master_numbers() -> None:
    engine = NumerologyEngine()

    # Life path 11: Nov 9, 1989 (Month 11, Day 9, Year 1989 -> 27 -> 9)
    # Sum: 11 + 9 + 9 = 29 -> 2 + 9 = 11
    dob_11 = datetime.date(1989, 11, 9)
    res_11 = engine.calculate_life_path(dob_11)
    assert res_11.calculated_value == 11
    assert any("2 + 9 = 11" in s for s in res_11.calculation_steps)

    # Life path 22: Jul 7, 1979 (Month 7, Day 7, Year 1979 -> 26 -> 8)
    # Sum: 7 + 7 + 8 = 22
    dob_22 = datetime.date(1979, 7, 7)
    res_22 = engine.calculate_life_path(dob_22)
    assert res_22.calculated_value == 22

    # Life path 33: Feb 9, 1975 (Month 2, Day 9, Year 1975 -> 22)
    # Sum: 2 + 9 + 22 = 33
    dob_33 = datetime.date(1975, 2, 9)
    res_33 = engine.calculate_life_path(dob_33)
    assert res_33.calculated_value == 33


def test_birthday_number() -> None:
    engine = NumerologyEngine()

    # Single digit
    res = engine.calculate_birthday_number(5)
    assert res.calculated_value == 5
    assert res.source_input == "5"

    # Reduced day: 12 -> 3
    res_12 = engine.calculate_birthday_number(12)
    assert res_12.calculated_value == 3

    # Master number day: 11 stays 11
    res_11 = engine.calculate_birthday_number(11)
    assert res_11.calculated_value == 11

    # Master number day: 22 stays 22
    res_22 = engine.calculate_birthday_number(22)
    assert res_22.calculated_value == 22

    # Day 29 -> 2 + 9 = 11
    res_29 = engine.calculate_birthday_number(29)
    assert res_29.calculated_value == 11

    # Boundary validations
    with pytest.raises(ValueError, match="Day must be between 1 and 31."):
        engine.calculate_birthday_number(0)

    with pytest.raises(ValueError, match="Day must be between 1 and 31."):
        engine.calculate_birthday_number(32)


def test_personal_year_and_month() -> None:
    engine = NumerologyEngine()
    dob = datetime.date(1990, 10, 12)

    # Personal Year for 2026
    # Month: 10 -> 1
    # Day: 12 -> 3
    # Year: 2026 -> 2 + 0 + 2 + 6 = 10 -> 1
    # Sum: 1 + 3 + 1 = 5
    py_res = engine.calculate_personal_year(dob, 2026)
    assert py_res.calculated_value == 5
    assert py_res.source_input == "DOB: 1990-10-12, Target Year: 2026"
    assert "Pythagorean Numerology System" in py_res.methodology

    # Personal Month for target month November (11) -> 2
    # Personal Year: 5 + Month: 2 = 7
    pm_res = engine.calculate_personal_month(dob, 2026, 11)
    assert pm_res.calculated_value == 7
    assert pm_res.source_input == "DOB: 1990-10-12, Target: 2026-11"

    # Validation errors
    with pytest.raises(ValueError, match="Target year must be a positive integer."):
        engine.calculate_personal_year(dob, 0)

    with pytest.raises(ValueError, match="Target month must be between 1 and 12."):
        engine.calculate_personal_month(dob, 2026, 13)

    with pytest.raises(ValueError, match="Target month must be between 1 and 12."):
        engine.calculate_personal_month(dob, 2026, 0)


def test_name_validation() -> None:
    engine = NumerologyEngine()
    assert engine.validate_name("  John   Doe  ") == "JOHN DOE"
    assert engine.validate_name("Alice Mary Smith") == "ALICE MARY SMITH"

    with pytest.raises(ValueError, match="Name cannot be empty."):
        engine.validate_name("")

    with pytest.raises(ValueError, match="Name cannot be empty."):
        engine.validate_name("   ")

    with pytest.raises(
        ValueError,
        match="Name must contain only alphabetic characters and spaces.",
    ):
        engine.validate_name("John Doe 123")

    with pytest.raises(
        ValueError,
        match="Name must contain only alphabetic characters and spaces.",
    ):
        engine.validate_name("John@Doe!")


def test_name_based_calculations() -> None:
    engine = NumerologyEngine()
    # Name: "John Doe"
    # Letters: J=1, O=6, H=8, N=5, D=4, O=6, E=5
    # Total sum: 1 + 6 + 8 + 5 + 4 + 6 + 5 = 35 -> 3 + 5 = 8
    destiny = engine.calculate_destiny_expression("John Doe")
    assert destiny.calculated_value == 8
    assert destiny.source_input == "John Doe"
    assert any("3 + 5 = 8" in s for s in destiny.calculation_steps)
    assert "Pythagorean Numerology System" in destiny.methodology

    # Vowels in John Doe: O=6, O=6, E=5 -> Sum = 17 -> 1 + 7 = 8
    soul = engine.calculate_soul_urge("John Doe")
    assert soul.calculated_value == 8
    assert soul.source_input == "John Doe"
    assert any("1 + 7 = 8" in s for s in soul.calculation_steps)

    # Consonants in John Doe: J=1, H=8, N=5, D=4 -> Sum = 18 -> 1 + 8 = 9
    personality = engine.calculate_personality_number("John Doe")
    assert personality.calculated_value == 9
    assert personality.source_input == "John Doe"
    assert any("1 + 8 = 9" in s for s in personality.calculation_steps)


def test_edge_cases_no_vowels_or_consonants() -> None:
    engine = NumerologyEngine()

    # Consonant-only abbreviation / name
    soul_no_vowels = engine.calculate_soul_urge("BRR")
    assert soul_no_vowels.calculated_value == 0
    assert "No vowels found in name" in soul_no_vowels.calculation_steps

    # Vowel-only name
    pers_no_cons = engine.calculate_personality_number("AIE")
    assert pers_no_cons.calculated_value == 0
    assert "No consonants found in name" in pers_no_cons.calculation_steps


def test_numerology_profile_generation() -> None:
    engine = NumerologyEngine()
    dob = datetime.date(1990, 10, 12)
    profile = engine.calculate_profile(dob, "John Doe", target_year=2026, target_month=11)

    assert isinstance(profile, NumerologyProfile)
    assert profile.life_path.calculated_value == 5
    assert profile.birthday_number.calculated_value == 3
    assert profile.destiny_expression.calculated_value == 8
    assert profile.soul_urge.calculated_value == 8
    assert profile.personality_number.calculated_value == 9
    assert profile.personal_year is not None and profile.personal_year.calculated_value == 5
    assert profile.personal_month is not None and profile.personal_month.calculated_value == 7
    assert profile.methodology == "Pythagorean Numerology System"
    assert profile.engine_version == "1.0.0"


def test_system_isolation_and_versioning() -> None:
    """Ensure non-Pythagorean systems are rejected and not mixed silently."""
    cfg = NumerologyConfig(engine_version="1.0.0", methodology=NumerologySystem.PYTHAGOREAN)
    engine = NumerologyEngine(cfg)
    assert engine.config.methodology == NumerologySystem.PYTHAGOREAN
    assert engine.config.engine_version == "1.0.0"

    # Custom / invalid methodology string in config should fail validation
    with pytest.raises(Exception):
        invalid_cfg = NumerologyConfig(methodology="Chaldean Numerology System")  # type: ignore[arg-type]
        NumerologyEngine(invalid_cfg)

