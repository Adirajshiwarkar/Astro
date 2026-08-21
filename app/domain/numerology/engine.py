import datetime

from app.domain.numerology.config import NumerologyConfig, NumerologySystem
from app.domain.numerology.models import (
    NumerologyCalculationResult,
    NumerologyProfile,
)

PYTHAGOREAN_VALUES: dict[str, int] = {
    "A": 1,
    "J": 1,
    "S": 1,
    "B": 2,
    "K": 2,
    "T": 2,
    "C": 3,
    "L": 3,
    "U": 3,
    "D": 4,
    "M": 4,
    "V": 4,
    "E": 5,
    "N": 5,
    "W": 5,
    "F": 6,
    "O": 6,
    "X": 6,
    "G": 7,
    "P": 7,
    "Y": 7,
    "H": 8,
    "Q": 8,
    "Z": 8,
    "I": 9,
    "R": 9,
}

VOWELS: set[str] = {"A", "E", "I", "O", "U"}


class NumerologyEngine:
    """Deterministic Western Pythagorean Numerology engine.

    Executes strictly numerical reductions and step-by-step arithmetic traces
    without generating prose. Numerology systems are strictly isolated.
    """

    def __init__(self, config: NumerologyConfig | None = None) -> None:
        self.config = config or NumerologyConfig()
        if self.config.methodology != NumerologySystem.PYTHAGOREAN:
            raise ValueError(
                f"Unsupported numerology methodology: {self.config.methodology}. "
                "Only Pythagorean Numerology System is supported in this version."
            )

    @property
    def system_name(self) -> str:
        if isinstance(self.config.methodology, NumerologySystem):
            return self.config.methodology.value
        return str(self.config.methodology)

    def _reduce_part(
        self, n: int, keep_master: bool | None = None
    ) -> tuple[int, list[str]]:
        """Reduce an integer to a single digit or master number (11, 22, 33)."""
        if keep_master is None:
            keep_master = self.config.preserve_master_numbers

        steps: list[str] = []
        curr = n
        if curr <= 0:
            return curr, steps

        while curr > 9:
            if keep_master and curr in self.config.master_numbers:
                break
            digits = [int(d) for d in str(curr)]
            next_val = sum(digits)
            steps.append(
                f"{' + '.join(str(d) for d in digits)} = {next_val}"
            )
            curr = next_val
        return curr, steps

    def validate_name(self, name: str) -> str:
        """Validate that name is not empty and consists only of alphabetic characters and spaces."""
        if not isinstance(name, str):
            raise ValueError("Name must be a string.")
        cleaned = " ".join(name.strip().split()).upper()
        if not cleaned:
            raise ValueError("Name cannot be empty.")
        # Ensure only alphabetic characters and single spaces remain
        if not all(c.isalpha() or c.isspace() for c in cleaned):
            raise ValueError(
                "Name must contain only alphabetic characters and spaces."
            )
        return cleaned

    def calculate_life_path(
        self, dob: datetime.date
    ) -> NumerologyCalculationResult:
        """Calculate Life Path number from birth date using 3-step Pythagorean reduction."""
        if not isinstance(dob, (datetime.date, datetime.datetime)):
            raise ValueError("Invalid date of birth.")

        m_val, m_steps = self._reduce_part(dob.month)
        d_val, d_steps = self._reduce_part(dob.day)
        y_val, y_steps = self._reduce_part(dob.year)

        sum_val = m_val + d_val + y_val
        final_val, final_steps = self._reduce_part(sum_val)

        steps = [
            f"Reduce Month: {dob.month} -> {m_val} (steps: {m_steps})",
            f"Reduce Day: {dob.day} -> {d_val} (steps: {d_steps})",
            f"Reduce Year: {dob.year} -> {y_val} (steps: {y_steps})",
            f"Sum reduced components: {m_val} + {d_val} + {y_val} = {sum_val}",
        ]
        if final_steps:
            steps.extend([f"Reduce Sum: {s}" for s in final_steps])

        return NumerologyCalculationResult(
            calculated_value=final_val,
            methodology=(
                f"{self.system_name}: Reduce month, day, and year individually "
                "to single digit or master number, sum them, and reduce the result."
            ),
            source_input=dob.isoformat(),
            calculation_steps=steps,
            engine_version=self.config.engine_version,
        )

    def calculate_birthday_number(
        self, day: int
    ) -> NumerologyCalculationResult:
        """Calculate Birthday Number from the day of birth."""
        if not (1 <= day <= 31):
            raise ValueError("Day must be between 1 and 31.")

        val, steps = self._reduce_part(day)
        steps_str = f" {steps}" if steps else ""
        return NumerologyCalculationResult(
            calculated_value=val,
            methodology=f"{self.system_name}: Reduce day of birth to a single digit or master number.",
            source_input=str(day),
            calculation_steps=[f"Reduce day {day}:{steps_str}"],
            engine_version=self.config.engine_version,
        )

    def calculate_personal_year(
        self, dob: datetime.date, target_year: int
    ) -> NumerologyCalculationResult:
        """Calculate Personal Year for a specific target year."""
        if not isinstance(dob, (datetime.date, datetime.datetime)):
            raise ValueError("Invalid date of birth.")
        if target_year <= 0:
            raise ValueError("Target year must be a positive integer.")

        m_val, m_steps = self._reduce_part(dob.month)
        d_val, d_steps = self._reduce_part(dob.day)
        y_val, y_steps = self._reduce_part(target_year)

        sum_val = m_val + d_val + y_val
        final_val, final_steps = self._reduce_part(sum_val)

        steps = [
            f"Reduce Month: {dob.month} -> {m_val} (steps: {m_steps})",
            f"Reduce Day: {dob.day} -> {d_val} (steps: {d_steps})",
            f"Reduce Target Year: {target_year} -> {y_val} (steps: {y_steps})",
            f"Sum components: {m_val} + {d_val} + {y_val} = {sum_val}",
        ]
        if final_steps:
            steps.extend([f"Reduce Sum: {s}" for s in final_steps])

        return NumerologyCalculationResult(
            calculated_value=final_val,
            methodology=(
                f"{self.system_name}: Sum reduced birth month, birth day, "
                "and target year, then reduce to single digit or master number."
            ),
            source_input=f"DOB: {dob.isoformat()}, Target Year: {target_year}",
            calculation_steps=steps,
            engine_version=self.config.engine_version,
        )

    def calculate_personal_month(
        self, dob: datetime.date, target_year: int, target_month: int
    ) -> NumerologyCalculationResult:
        """Calculate Personal Month for a specific target year and month."""
        if not (1 <= target_month <= 12):
            raise ValueError("Target month must be between 1 and 12.")

        py_res = self.calculate_personal_year(dob, target_year)
        py_val = py_res.calculated_value

        m_val, m_steps = self._reduce_part(target_month)
        sum_val = py_val + m_val
        final_val, final_steps = self._reduce_part(sum_val)

        steps = [
            f"Personal Year value: {py_val}",
            f"Reduce Target Month: {target_month} -> {m_val} (steps: {m_steps})",
            f"Sum components: {py_val} + {m_val} = {sum_val}",
        ]
        if final_steps:
            steps.extend([f"Reduce Sum: {s}" for s in final_steps])

        return NumerologyCalculationResult(
            calculated_value=final_val,
            methodology=(
                f"{self.system_name}: Sum Personal Year value and reduced "
                "target month, then reduce to single digit or master number."
            ),
            source_input=f"DOB: {dob.isoformat()}, Target: {target_year}-{target_month:02d}",
            calculation_steps=steps,
            engine_version=self.config.engine_version,
        )

    def calculate_destiny_expression(
        self, name: str
    ) -> NumerologyCalculationResult:
        """Calculate Destiny/Expression number from full name."""
        cleaned_name = self.validate_name(name)
        letters = [c for c in cleaned_name if c.isalpha()]

        letter_values = [PYTHAGOREAN_VALUES[c] for c in letters]
        sum_val = sum(letter_values)
        final_val, final_steps = self._reduce_part(sum_val)

        mapping_str = ", ".join(
            f"{c}={PYTHAGOREAN_VALUES[c]}" for c in letters
        )
        steps = [
            f"Map letters to values: {mapping_str}",
            f"Sum of letter values: {sum_val}",
        ]
        if final_steps:
            steps.extend([f"Reduce Sum: {s}" for s in final_steps])

        return NumerologyCalculationResult(
            calculated_value=final_val,
            methodology=(
                f"{self.system_name}: Sum Pythagorean values of all letters "
                "in full name, then reduce to single digit or master number."
            ),
            source_input=name,
            calculation_steps=steps,
            engine_version=self.config.engine_version,
        )

    def calculate_soul_urge(self, name: str) -> NumerologyCalculationResult:
        """Calculate Soul Urge (Heart's Desire) number from vowels of full name."""
        cleaned_name = self.validate_name(name)
        vowels = [c for c in cleaned_name if c in VOWELS]

        if not vowels:
            return NumerologyCalculationResult(
                calculated_value=0,
                methodology=(
                    f"{self.system_name}: Sum Pythagorean values of all vowels "
                    "in full name, then reduce to single digit or master number."
                ),
                source_input=name,
                calculation_steps=["No vowels found in name"],
                engine_version=self.config.engine_version,
            )

        vowel_values = [PYTHAGOREAN_VALUES[c] for c in vowels]
        sum_val = sum(vowel_values)
        final_val, final_steps = self._reduce_part(sum_val)

        mapping_str = ", ".join(
            f"{c}={PYTHAGOREAN_VALUES[c]}" for c in vowels
        )
        steps = [
            f"Vowels found: {vowels}",
            f"Map vowels to values: {mapping_str}",
            f"Sum of vowel values: {sum_val}",
        ]
        if final_steps:
            steps.extend([f"Reduce Sum: {s}" for s in final_steps])

        return NumerologyCalculationResult(
            calculated_value=final_val,
            methodology=(
                f"{self.system_name}: Sum Pythagorean values of all vowels "
                "in full name, then reduce to single digit or master number."
            ),
            source_input=name,
            calculation_steps=steps,
            engine_version=self.config.engine_version,
        )

    def calculate_personality_number(
        self, name: str
    ) -> NumerologyCalculationResult:
        """Calculate Personality number from consonants of full name."""
        cleaned_name = self.validate_name(name)
        consonants = [
            c for c in cleaned_name if c.isalpha() and c not in VOWELS
        ]

        if not consonants:
            return NumerologyCalculationResult(
                calculated_value=0,
                methodology=(
                    f"{self.system_name}: Sum Pythagorean values of all consonants "
                    "in full name, then reduce to single digit or master number."
                ),
                source_input=name,
                calculation_steps=["No consonants found in name"],
                engine_version=self.config.engine_version,
            )

        consonant_values = [PYTHAGOREAN_VALUES[c] for c in consonants]
        sum_val = sum(consonant_values)
        final_val, final_steps = self._reduce_part(sum_val)

        mapping_str = ", ".join(
            f"{c}={PYTHAGOREAN_VALUES[c]}" for c in consonants
        )
        steps = [
            f"Consonants found: {consonants}",
            f"Map consonants to values: {mapping_str}",
            f"Sum of consonant values: {sum_val}",
        ]
        if final_steps:
            steps.extend([f"Reduce Sum: {s}" for s in final_steps])

        return NumerologyCalculationResult(
            calculated_value=final_val,
            methodology=(
                f"{self.system_name}: Sum Pythagorean values of all consonants "
                "in full name, then reduce to single digit or master number."
            ),
            source_input=name,
            calculation_steps=steps,
            engine_version=self.config.engine_version,
        )

    def calculate_profile(
        self,
        dob: datetime.date,
        name: str,
        target_year: int | None = None,
        target_month: int | None = None,
    ) -> NumerologyProfile:
        """Calculate full Numerology Profile containing Life Path, Birthday, Destiny, Soul Urge, and Personality."""
        personal_year = (
            self.calculate_personal_year(dob, target_year)
            if target_year is not None
            else None
        )
        personal_month = (
            self.calculate_personal_month(dob, target_year, target_month)
            if (target_year is not None and target_month is not None)
            else None
        )

        return NumerologyProfile(
            life_path=self.calculate_life_path(dob),
            birthday_number=self.calculate_birthday_number(dob.day),
            destiny_expression=self.calculate_destiny_expression(name),
            soul_urge=self.calculate_soul_urge(name),
            personality_number=self.calculate_personality_number(name),
            personal_year=personal_year,
            personal_month=personal_month,
            methodology=self.system_name,
            engine_version=self.config.engine_version,
        )

