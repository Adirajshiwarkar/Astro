from typing import Any

from app.domain.canonical.comparator import ChartComparator
from app.domain.canonical.models import (
    CanonicalChartRepresentation,
    ComparisonResult,
    ComparisonStatus,
    ValidationReport,
    ValidationStatus,
)
from app.domain.canonical.normalizer import ChartNormalizer
from app.domain.image_intelligence.models import StructuredChartRepresentation
from app.domain.vedic.models import VedicChart


class ChartValidationService:
    """Orchestrates multi-source chart verification, comparing image extraction

    and independent calculations without silently overwriting either source.
    """

    def __init__(
        self,
        normalizer: ChartNormalizer | None = None,
        comparator: ChartComparator | None = None,
    ) -> None:
        self.normalizer = normalizer or ChartNormalizer()
        self.comparator = comparator or ChartComparator()

    def validate_dual_sources(
        self,
        source_a_data: CanonicalChartRepresentation | StructuredChartRepresentation | VedicChart | dict[str, Any],
        source_b_data: CanonicalChartRepresentation | StructuredChartRepresentation | VedicChart | dict[str, Any],
    ) -> ValidationReport:
        """Validate and cross-check two chart sources without overwriting either."""
        # 1. Normalize Source A
        chart_a = self._normalize_input(source_a_data)

        # 2. Normalize Source B
        chart_b = self._normalize_input(source_b_data)

        # 3. Compare Normalized Charts
        comparison_res = self.comparator.compare(chart_a, chart_b)

        # 4. Partition comparisons
        matching = [c for c in comparison_res.field_comparisons if c.status == ComparisonStatus.MATCH]
        conflicts = [c for c in comparison_res.field_comparisons if c.status == ComparisonStatus.CONFLICT]
        missing = [
            c
            for c in comparison_res.field_comparisons
            if c.status in (ComparisonStatus.MISSING_IN_A, ComparisonStatus.MISSING_IN_B)
        ]
        low_conf = [c for c in comparison_res.field_comparisons if c.status == ComparisonStatus.LOW_CONFIDENCE]

        # 5. Determine Overall Validation Status
        if len(conflicts) > 0:
            status = ValidationStatus.DISCREPANCIES_FOUND
            summary = (
                f"Discrepancies detected between Source A ({chart_a.provenance.source}) and "
                f"Source B ({chart_b.provenance.source}). {len(conflicts)} conflicting fields found."
            )
        elif len(low_conf) > 0:
            status = ValidationStatus.HIGH_UNCERTAINTY
            summary = (
                f"High uncertainty detected due to {len(low_conf)} low-confidence extraction fields "
                f"in Source A ({chart_a.provenance.source})."
            )
        elif len(missing) > 0 and comparison_res.match_percentage < 90.0:
            status = ValidationStatus.PARTIAL_MATCH
            summary = (
                f"Partial match between sources ({comparison_res.match_percentage:.1f}%). "
                f"{len(missing)} fields missing in one of the sources."
            )
        else:
            status = ValidationStatus.VERIFIED
            summary = (
                f"Chart verified successfully across both sources with {comparison_res.match_percentage:.1f}% match rate "
                f"and 0 conflicts."
            )

        source_a_summary = {
            "source": chart_a.provenance.source,
            "method": chart_a.provenance.method,
            "confidence": chart_a.provenance.confidence,
            "total_planets": len(chart_a.planets),
            "has_ascendant": chart_a.ascendant is not None,
        }

        source_b_summary = {
            "source": chart_b.provenance.source,
            "method": chart_b.provenance.method,
            "confidence": chart_b.provenance.confidence,
            "total_planets": len(chart_b.planets),
            "has_ascendant": chart_b.ascendant is not None,
        }

        return ValidationReport(
            status=status,
            match_percentage=comparison_res.match_percentage,
            summary=summary,
            source_a_summary=source_a_summary,
            source_b_summary=source_b_summary,
            matching_fields=matching,
            conflicts=conflicts,
            missing_fields=missing,
            low_confidence_fields=low_conf,
            comparison_result=comparison_res,
            chart_a=chart_a,
            chart_b=chart_b,
        )

    def _normalize_input(self, data: Any) -> CanonicalChartRepresentation:
        if isinstance(data, CanonicalChartRepresentation):
            return data
        if isinstance(data, StructuredChartRepresentation):
            return self.normalizer.from_image_extraction(data)
        if isinstance(data, VedicChart):
            return self.normalizer.from_vedic_chart(data)
        if isinstance(data, dict):
            return self.normalizer.from_ephemeris_dict(data)
        raise ValueError(f"Unsupported chart data format for canonical normalization: {type(data)}")
