import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1.deps import get_current_user
from app.db.session import get_db_session
from app.db.models import User
from app.domain.astrology.engine import WesternAstrologyEngine
from app.domain.prediction.timeline import TimelineEngine
from app.domain.prediction.scenario import ScenarioEngine
from app.schemas.predictions import PredictionRequest, PredictionResponse
from app.services.astrology.provider import SwissEphemerisProvider
from app.services.astrology.timezone import local_to_utc

router = APIRouter()


@router.post(
    "",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_predictions(
    request: PredictionRequest,
    current_user: User = Depends(get_current_user),
) -> PredictionResponse:
    """Generate time partitioned scenarios and predictions based on birth parameters."""
    try:
        # Convert local time to UTC using local_to_utc (returns (utc_dt, is_dst))
        utc_dt, _ = local_to_utc(
            request.birth_data.date_of_birth,
            request.birth_data.birth_time,
            request.birth_data.timezone,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Time normalization failed: {str(e)}",
        ) from e

    try:
        # 1. Compute natal chart
        provider = SwissEphemerisProvider()
        zodiac_type = "tropical" if request.system.lower() == "western" else "sidereal"
        raw_data = provider.calculate_chart(
            utc_dt=utc_dt,
            latitude=request.birth_data.latitude,
            longitude=request.birth_data.longitude,
            zodiac_type=zodiac_type,
            ayanamsa=request.birth_data.calculation_metadata.get(
                "ayanamsa", "lahiri"
            ),
            house_system=request.birth_data.calculation_metadata.get(
                "house_system", "placidus"
            ),
        )

        engine = WesternAstrologyEngine()
        calculated_chart = engine.calculate_natal_chart(raw_data)

        # 2. Run timeline partition
        timeline_engine = TimelineEngine()
        start_date = datetime.date.today()

        # Map request timeframe to ForecastingWindow
        from app.domain.prediction.models import ForecastingWindow, TimeWindowConfig
        window_type = ForecastingWindow.SIX_MONTHS
        tf_lower = request.timeframe.lower()
        if "week" in tf_lower or "1_month" in tf_lower or "one_month" in tf_lower or "monthly" in tf_lower:
            window_type = ForecastingWindow.ONE_MONTH
        elif "three" in tf_lower or "3_month" in tf_lower or "quarter" in tf_lower:
            window_type = ForecastingWindow.THREE_MONTHS

        # Map derived factors to AstrologicalSignals for timeline engine
        from app.domain.signals.models import (
            AstrologicalSignal,
            FactorPolarity,
            SignalDomain,
            SignalFactor,
            SignalType,
            SourceSystem,
        )

        signals = []
        for factor in calculated_chart.derived_factors:
            sf = SignalFactor(
                factor_id=f"FACT-{uuid.uuid4().hex[:6].upper()}",
                name=factor.calculation,
                source_system=SourceSystem.WESTERN if request.system.lower() == "western" else SourceSystem.VEDIC,
                weight=factor.strength,
                polarity=FactorPolarity.POSITIVE,
                description=factor.methodology,
                timeframe=factor.timeframe
            )
            sig = AstrologicalSignal(
                signal_id=f"SIG-{uuid.uuid4().hex[:6].upper()}",
                domain=SignalDomain.CAREER if "house 10" in factor.calculation.lower() or "mc" in factor.calculation.lower() else SignalDomain.PERSONAL_DEVELOPMENT,
                signal_type=SignalType.OPPORTUNITY,
                strength=factor.strength,
                timeframe="2026",
                source_system=SourceSystem.WESTERN if request.system.lower() == "western" else SourceSystem.VEDIC,
                supporting_factors=[sf],
                conflicting_factors=[],
                rule_version=factor.engine_version,
                correlation_score=1.0
            )
            signals.append(sig)

        time_window = TimeWindowConfig(
            window_type=window_type,
            start_date=start_date
        )
        forecast = timeline_engine.generate_timeline(
            signals=signals,
            time_window=time_window
        )

        # 3. Generate scenarios
        scenario_engine = ScenarioEngine()
        scenario_set = scenario_engine.generate_scenarios(
            domain=SignalDomain.CAREER,
            signals=signals,
            evidence=[],  # Empty list of evidence
            timeframe=request.timeframe
        )

        # Map to dict responses
        timeline_dict = {
            "total_intervals": len(forecast.intervals),
            "intervals": [
                {
                    "start_date": interval.start_date.isoformat(),
                    "end_date": interval.end_date.isoformat(),
                    "active_signals": [
                        {
                            "signal_id": s.signal_id,
                            "domain": s.domain.value,
                            "signal_type": s.signal_type.value,
                            "strength": s.strength,
                            "timeframe": s.timeframe,
                            "source_system": s.source_system.value,
                        }
                        for s in interval.active_signals
                    ]
                }
                for interval in forecast.intervals
            ]
        }

        scenarios_list = [
            {
                "scenario_id": scen.scenario_id,
                "domain": scen.domain,
                "timeframe": scen.timeframe,
                "support_score": scen.support_score,
                "evidence": scen.evidence,
                "supporting_signals": scen.supporting_signals,
                "conflicting_signals": scen.conflicting_signals,
                "uncertainty": scen.uncertainty
            }
            for scen in [scenario_set.primary, scenario_set.alternative, scenario_set.challenge]
            if scen is not None
        ]

        return PredictionResponse(
            prediction_id=uuid.uuid4(),
            system=request.system,
            timeframe=request.timeframe,
            timeline=timeline_dict,
            scenarios=scenarios_list,
            created_at=datetime.datetime.now(datetime.UTC),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction calculation failed: {str(e)}",
        ) from e


@router.get(
    "/{id}",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
)
async def get_prediction_by_id(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_session),
) -> PredictionResponse:
    """Retrieve prediction details by ID."""
    # Since predictions are dynamic, we generate a mock or lookup.
    # Return a deterministic mock response for the given ID.
    timeline_dict = {
        "total_intervals": 1,
        "intervals": [
            {
                "start_date": datetime.date.today().isoformat(),
                "end_date": (datetime.date.today() + datetime.timedelta(days=7)).isoformat(),
                "active_signals": [
                    {
                        "signal_id": "SIG-SUN-TRANSIT",
                        "name": "Sun Transit 10th House",
                        "domain": "career",
                        "strength": 0.85,
                        "description": "Sun transiting the karmic career house"
                    }
                ]
            }
        ]
    }
    
    scenarios_list = [
        {
            "scenario_id": "SCEN-CAREER-PRIMARY",
            "domain": "career",
            "timeframe": "monthly",
            "support_score": 0.9,
            "evidence": ["Transit Sun forms conjunction with Midheaven"],
            "supporting_signals": ["SIG-SUN-TRANSIT"],
            "conflicting_signals": [],
            "uncertainty": "low"
        }
    ]

    return PredictionResponse(
        prediction_id=id,
        system="Western",
        timeframe="weekly",
        timeline=timeline_dict,
        scenarios=scenarios_list,
        created_at=datetime.datetime.now(datetime.UTC),
    )
