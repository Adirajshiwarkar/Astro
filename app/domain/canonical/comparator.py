from typing import Any

from app.domain.canonical.models import (
    CanonicalChartRepresentation,
    CanonicalField,
    ComparisonResult,
    ComparisonStatus,
    FieldComparison,
    ProvenanceMetadata,
)


class ChartComparator:
    """Compares two CanonicalChartRepresentation instances and detects matches, conflicts,

    missing values, and low-confidence extractions without overwriting sources.
    """

    def __init__(
        self,
        degree_tolerance: float = 1.0,  # Degrees +/- tolerance
        low_confidence_threshold: float = 0.75,
    ) -> None:
        self.degree_tolerance = degree_tolerance
        self.low_confidence_threshold = low_confidence_threshold

    def _compare_scalar(
        self,
        field_name: str,
        field_a: CanonicalField[Any] | None,
        field_b: CanonicalField[Any] | None,
        is_numeric: bool = False,
    ) -> FieldComparison:
        val_a = field_a.value if field_a is not None else None
        prov_a = field_a.provenance if field_a is not None else None
        val_b = field_b.value if field_b is not None else None
        prov_b = field_b.provenance if field_b is not None else None

        # Check missing
        if field_a is None and field_b is not None:
            return FieldComparison(
                field_name=field_name,
                status=ComparisonStatus.MISSING_IN_A,
                value_a=None,
                provenance_a=None,
                value_b=val_b,
                provenance_b=prov_b,
                diff_details=f"Present in Source B ({val_b}) but missing in Source A.",
            )

        if field_a is not None and field_b is None:
            return FieldComparison(
                field_name=field_name,
                status=ComparisonStatus.MISSING_IN_B,
                value_a=val_a,
                provenance_a=prov_a,
                value_b=None,
                provenance_b=None,
                diff_details=f"Present in Source A ({val_a}) but missing in Source B.",
            )

        if field_a is None and field_b is None:
            return FieldComparison(
                field_name=field_name,
                status=ComparisonStatus.MATCH,
                value_a=None,
                value_b=None,
                diff_details="Both sources absent.",
            )

        # Check low confidence in A
        if prov_a and prov_a.confidence < self.low_confidence_threshold:
            return FieldComparison(
                field_name=field_name,
                status=ComparisonStatus.LOW_CONFIDENCE,
                value_a=val_a,
                provenance_a=prov_a,
                value_b=val_b,
                provenance_b=prov_b,
                diff_details=f"Low extraction confidence ({prov_a.confidence:.2f}) in Source A.",
            )

        # Compare values
        if is_numeric and isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
            diff = abs(float(val_a) - float(val_b))
            if diff <= self.degree_tolerance:
                return FieldComparison(
                    field_name=field_name,
                    status=ComparisonStatus.MATCH,
                    value_a=val_a,
                    provenance_a=prov_a,
                    value_b=val_b,
                    provenance_b=prov_b,
                    diff_details=f"Numeric match within tolerance (diff: {diff:.3f}°).",
                )
            else:
                return FieldComparison(
                    field_name=field_name,
                    status=ComparisonStatus.CONFLICT,
                    value_a=val_a,
                    provenance_a=prov_a,
                    value_b=val_b,
                    provenance_b=prov_b,
                    diff_details=f"Numeric discrepancy exceeds tolerance (A={val_a}, B={val_b}, diff={diff:.3f}°).",
                )

        # String / boolean / integer exact match
        str_a = str(val_a).strip().lower() if val_a is not None else ""
        str_b = str(val_b).strip().lower() if val_b is not None else ""

        if str_a == str_b:
            return FieldComparison(
                field_name=field_name,
                status=ComparisonStatus.MATCH,
                value_a=val_a,
                provenance_a=prov_a,
                value_b=val_b,
                diff_details="Exact match.",
            )
        else:
            return FieldComparison(
                field_name=field_name,
                status=ComparisonStatus.CONFLICT,
                value_a=val_a,
                provenance_a=prov_a,
                value_b=val_b,
                provenance_b=prov_b,
                diff_details=f"Value conflict (Source A='{val_a}', Source B='{val_b}').",
            )

    def compare(
        self,
        chart_a: CanonicalChartRepresentation,
        chart_b: CanonicalChartRepresentation,
    ) -> ComparisonResult:
        """Compare chart_a against chart_b field by field."""
        comparisons: list[FieldComparison] = []

        # 1. Compare Ascendant
        if chart_a.ascendant or chart_b.ascendant:
            asc_a = chart_a.ascendant
            asc_b = chart_b.ascendant

            comparisons.append(
                self._compare_scalar(
                    "Ascendant.sign",
                    asc_a.sign if asc_a else None,
                    asc_b.sign if asc_b else None,
                )
            )
            comparisons.append(
                self._compare_scalar(
                    "Ascendant.degree",
                    asc_a.degree if asc_a else None,
                    asc_b.degree if asc_b else None,
                    is_numeric=True,
                )
            )
            comparisons.append(
                self._compare_scalar(
                    "Ascendant.nakshatra",
                    asc_a.nakshatra if asc_a else None,
                    asc_b.nakshatra if asc_b else None,
                )
            )
            comparisons.append(
                self._compare_scalar(
                    "Ascendant.pada",
                    asc_a.pada if asc_a else None,
                    asc_b.pada if asc_b else None,
                )
            )

        # 2. Compare Planets
        all_planets = set(chart_a.planets.keys()) | set(chart_b.planets.keys())
        for p_name in sorted(all_planets):
            pa = chart_a.planets.get(p_name)
            pb = chart_b.planets.get(p_name)

            if pa is None and pb is not None:
                comparisons.append(
                    FieldComparison(
                        field_name=f"Planet[{p_name}]",
                        status=ComparisonStatus.MISSING_IN_A,
                        value_a=None,
                        value_b=pb.planet.value,
                        provenance_b=pb.planet.provenance,
                        diff_details=f"Planet {p_name} missing from Source A.",
                    )
                )
                continue

            if pa is not None and pb is None:
                comparisons.append(
                    FieldComparison(
                        field_name=f"Planet[{p_name}]",
                        status=ComparisonStatus.MISSING_IN_B,
                        value_a=pa.planet.value,
                        provenance_a=pa.planet.provenance,
                        value_b=None,
                        diff_details=f"Planet {p_name} missing from Source B.",
                    )
                )
                continue

            if pa and pb:
                # Compare Sign
                comparisons.append(
                    self._compare_scalar(
                        f"Planet[{p_name}].sign",
                        pa.sign,
                        pb.sign,
                    )
                )
                # Compare House
                comparisons.append(
                    self._compare_scalar(
                        f"Planet[{p_name}].house",
                        pa.house,
                        pb.house,
                    )
                )
                # Compare Degree
                comparisons.append(
                    self._compare_scalar(
                        f"Planet[{p_name}].degree",
                        pa.degree,
                        pb.degree,
                        is_numeric=True,
                    )
                )
                # Compare Nakshatra
                if pa.nakshatra or pb.nakshatra:
                    comparisons.append(
                        self._compare_scalar(
                            f"Planet[{p_name}].nakshatra",
                            pa.nakshatra,
                            pb.nakshatra,
                        )
                    )
                # Compare Pada
                if pa.pada or pb.pada:
                    comparisons.append(
                        self._compare_scalar(
                            f"Planet[{p_name}].pada",
                            pa.pada,
                            pb.pada,
                        )
                    )
                # Compare Retrograde
                if pa.is_retrograde or pb.is_retrograde:
                    comparisons.append(
                        self._compare_scalar(
                            f"Planet[{p_name}].is_retrograde",
                            pa.is_retrograde,
                            pb.is_retrograde,
                        )
                    )

        # 3. Compare Houses
        houses_a = {h.house_number.value: h for h in chart_a.houses}
        houses_b = {h.house_number.value: h for h in chart_b.houses}
        all_houses = set(houses_a.keys()) | set(houses_b.keys())
        for h_num in sorted(all_houses):
            ha = houses_a.get(h_num)
            hb = houses_b.get(h_num)
            if ha and hb and (ha.sign or hb.sign):
                comparisons.append(
                    self._compare_scalar(
                        f"House[{h_num}].sign",
                        ha.sign,
                        hb.sign,
                    )
                )

        # Statistics computation
        total = len(comparisons)
        matches = sum(1 for c in comparisons if c.status == ComparisonStatus.MATCH)
        conflicts = sum(1 for c in comparisons if c.status == ComparisonStatus.CONFLICT)
        missing_a = sum(1 for c in comparisons if c.status == ComparisonStatus.MISSING_IN_A)
        missing_b = sum(1 for c in comparisons if c.status == ComparisonStatus.MISSING_IN_B)
        low_conf = sum(1 for c in comparisons if c.status == ComparisonStatus.LOW_CONFIDENCE)

        # Match percentage calculation (excluding elements missing in both)
        match_pct = round((matches / total * 100.0), 2) if total > 0 else 100.0

        return ComparisonResult(
            total_compared=total,
            matches=matches,
            conflicts=conflicts,
            missing_in_a=missing_a,
            missing_in_b=missing_b,
            low_confidence_count=low_conf,
            match_percentage=match_pct,
            field_comparisons=comparisons,
        )
