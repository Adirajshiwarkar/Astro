from typing import Any

from app.domain.context.models import ContextPackage, VersionMetadata


def to_dict_or_list(obj: Any) -> Any:
    """Helper to convert Pydantic objects or nested structures to standard Python dicts/lists."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, list):
        return [to_dict_or_list(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_dict_or_list(v) for k, v in obj.items()}
    return obj


class ContextBuilder:
    """Assembles and filters context for LLM prompts, preventing database dumps and context stuffing."""

    def __init__(
        self,
        astrology_engine_version: str = "1.0.0",
        prediction_rules_version: str = "1.0.0",
        knowledge_version: str = "1.0.0",
        prompt_version: str = "1.0.0",
    ) -> None:
        self.versions = VersionMetadata(
            astrology_engine_version=astrology_engine_version,
            prediction_rules_version=prediction_rules_version,
            knowledge_version=knowledge_version,
            prompt_version=prompt_version,
        )

    def detect_system(self, query: str) -> str | None:
        """Detect the target system from keywords in user query."""
        q_lower = query.lower()

        vedic_terms = [
            "vedic", "jyotish", "bhava", "graha", "rashi", "dasha", "dasa",
            "lagna", "surya", "chandra", "shani", "parashara"
        ]
        western_terms = [
            "western", "house", "planet", "sign", "aspect", "placidus",
            "midheaven", "trine", "square", "conjunction"
        ]
        numerology_terms = [
            "numerology", "personal year", "life path", "soul urge", "expression number"
        ]

        if any(t in q_lower for t in vedic_terms):
            return "Vedic"
        if any(t in q_lower for t in western_terms):
            return "Western"
        if any(t in q_lower for t in numerology_terms):
            return "Numerology"

        return None

    def detect_domains(self, query: str) -> list[str]:
        """Detect target life domains from query terms."""
        q_lower = query.lower()
        domains = []
        domain_mapping = {
            "career": ["career", "job", "profession", "work", "boss", "promotion", "midheaven", "10th house", "karma bhava"],
            "finance": ["finance", "money", "wealth", "income", "debt", "investment", "2nd house", "8th house", "dhana"],
            "relationship": ["relationship", "love", "marriage", "partner", "wife", "husband", "7th house", "yuvati"],
            "health": ["health", "disease", "illness", "wellness", "6th house", "8th house", "12th house", "roga"],
        }
        for dom, keywords in domain_mapping.items():
            if any(kw in q_lower for kw in keywords):
                domains.append(dom)
        return domains

    def build_context(
        self,
        query: str,
        chart: Any | None = None,
        western_factors: Any | None = None,
        vedic_factors: Any | None = None,
        numerology_factors: Any | None = None,
        signals: Any | None = None,
        evidence: Any | None = None,
        predictions: Any | None = None,
        timeline: Any | None = None,
        scenarios: Any | None = None,
        rag_results: Any | None = None,
        relevant_memory: Any | None = None,
        chart_validation_results: Any | None = None,
    ) -> ContextPackage:
        """Filter and compile inputs to form the ContextPackage package."""
        system = self.detect_system(query)
        domains = self.detect_domains(query)

        # Normalize inputs to dictionaries/lists
        chart_d = to_dict_or_list(chart)
        western_d = to_dict_or_list(western_factors)
        vedic_d = to_dict_or_list(vedic_factors)
        num_d = to_dict_or_list(numerology_factors)
        signals_d = to_dict_or_list(signals) or []
        evidence_d = to_dict_or_list(evidence) or []
        predictions_d = to_dict_or_list(predictions) or []
        timeline_d = to_dict_or_list(timeline)
        scenarios_d = to_dict_or_list(scenarios) or []
        rag_d = to_dict_or_list(rag_results) or []
        memory_d = to_dict_or_list(relevant_memory) or []
        validation_d = to_dict_or_list(chart_validation_results)

        # 1. Filter factors by system relevance
        filtered_western = None
        filtered_vedic = None
        filtered_numerology = None

        if system == "Western":
            filtered_western = western_d
        elif system == "Vedic":
            filtered_vedic = vedic_d
        elif system == "Numerology":
            filtered_numerology = num_d
        else:
            # Include top 5 of each as a fallback
            filtered_western = western_d[:5] if western_d else None
            filtered_vedic = vedic_d[:5] if vedic_d else None
            filtered_numerology = num_d[:5] if num_d else None

        # 2. Trim chart details to keep only relevant fields
        filtered_chart = None
        if chart_d:
            allowed_keys = {"birth_date", "birth_time", "latitude", "longitude", "timezone"}
            if system == "Western":
                filtered_chart = {k: v for k, v in chart_d.items() if "western" in k.lower() or k in allowed_keys}
            elif system == "Vedic":
                filtered_chart = {k: v for k, v in chart_d.items() if "vedic" in k.lower() or k in allowed_keys}
            else:
                filtered_chart = {k: v for k, v in chart_d.items() if k in allowed_keys}

        # 3. Filter signals by domain
        filtered_signals = []
        for s in signals_d:
            s_domain = s.get("domain", "").lower()
            if not domains or s_domain in domains:
                filtered_signals.append(s)
        filtered_signals = filtered_signals[:5]

        # 4. Filter evidence associated with filtered signals or matching domain
        filtered_evidence = []
        relevant_sig_ids = {s.get("signal_id") for s in filtered_signals if s.get("signal_id")}
        for e in evidence_d:
            e_id = e.get("evidence_id", "")
            sig_ref = e.get("signal_id", "")
            if sig_ref in relevant_sig_ids or not domains or any(d in e_id.lower() for d in domains):
                filtered_evidence.append(e)
        filtered_evidence = filtered_evidence[:5]

        # 5. Filter predictions by domain
        filtered_predictions = []
        for p in predictions_d:
            p_domain = p.get("domain", "").lower() if p.get("domain") else ""
            if not domains or p_domain in domains:
                filtered_predictions.append(p)
        filtered_predictions = filtered_predictions[:3]

        # 6. Filter scenarios by domain
        filtered_scenarios = []
        for sc in scenarios_d:
            sc_domain = sc.get("domain", "").lower() if sc.get("domain") else ""
            if not domains or sc_domain in domains:
                filtered_scenarios.append(sc)
        filtered_scenarios = filtered_scenarios[:3]

        # 7. Trim timeline active signals
        filtered_timeline = None
        if timeline_d:
            intervals = []
            for interval in timeline_d.get("intervals", []):
                active_sigs = interval.get("active_signals", [])
                filtered_active = [
                    sig for sig in active_sigs
                    if not domains or sig.get("domain", "").lower() in domains
                ]
                interval_copy = dict(interval)
                interval_copy["active_signals"] = filtered_active[:3]
                intervals.append(interval_copy)
            filtered_timeline = {
                "intervals": intervals,
                "total_intervals": timeline_d.get("total_intervals", 0)
            }

        # 8. Filter RAG matches
        filtered_rag = []
        for r in rag_d:
            r_system = r.get("system", "")
            if not system or r_system == system:
                filtered_rag.append(r)
        filtered_rag = filtered_rag[:3]

        # 9. Trim memory logs
        filtered_memory = memory_d[:3]

        # 10. Trim validation logs
        filtered_validation = None
        if validation_d:
            filtered_validation = {
                "is_valid": validation_d.get("is_valid", True),
                "errors": validation_d.get("errors", [])[:2],
                "warnings": validation_d.get("warnings", [])[:2],
            }

        return ContextPackage(
            query=query,
            relevant_system=system,
            relevant_domains=domains,
            chart=filtered_chart,
            western_factors=filtered_western,
            vedic_factors=filtered_vedic,
            numerology_factors=filtered_numerology,
            signals=filtered_signals,
            evidence=filtered_evidence,
            predictions=filtered_predictions,
            timeline=filtered_timeline,
            scenarios=filtered_scenarios,
            rag_results=filtered_rag,
            relevant_memory=filtered_memory,
            chart_validation_results=filtered_validation,
            version_metadata=self.versions,
        )
