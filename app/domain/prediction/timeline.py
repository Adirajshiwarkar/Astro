import datetime
import re

from app.domain.prediction.models import (
    ForecastingWindow,
    TimelineForecast,
    TimelineInterval,
    TimeWindowConfig,
)
from app.domain.signals.models import AstrologicalSignal


class TimelineEngine:
    """TimelineEngine partitions requested forecast periods into meaningful intervals

    and associates active signals with each interval.
    """

    def __init__(self, engine_version: str = "1.0.0") -> None:
        self.engine_version = engine_version

    def is_signal_active_in_interval(
        self, signal: AstrologicalSignal, start_date: datetime.date, end_date: datetime.date
    ) -> bool:
        """Deterministically determine if a signal is active within a specific interval."""
        timeframe = signal.timeframe.lower()

        # Natal signals are always active
        if "natal" in timeframe:
            return True

        # Check if timeframe mentions any 4-digit year, e.g. "2026"
        years = re.findall(r"\b(19\d\d|20\d\d)\b", timeframe)
        if years:
            for y_str in years:
                year = int(y_str)
                year_start = datetime.date(year, 1, 1)
                year_end = datetime.date(year, 12, 31)
                if not (end_date < year_start or start_date > year_end):
                    return True
            return False

        # Check if timeframe is an explicit date range like "2026-08-18 to 2027-02-16"
        dates = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", timeframe)
        if len(dates) == 2:
            try:
                tf_start = datetime.date.fromisoformat(dates[0])
                tf_end = datetime.date.fromisoformat(dates[1])
                return not (end_date < tf_start or start_date > tf_end)
            except ValueError:
                pass

        # Personal year cycles or other general cycles are active during the forecast
        if "personal year" in timeframe or "cycle" in timeframe:
            return True

        return True

    def generate_timeline(
        self, signals: list[AstrologicalSignal], time_window: TimeWindowConfig
    ) -> TimelineForecast:
        """Partition the time window into intervals and assign active signals to each interval."""
        start_date = time_window.start_date
        end_date = time_window.get_end_date()
        total_days = (end_date - start_date).days

        # Partitioning logic
        intervals_data: list[tuple[datetime.date, datetime.date, str]] = []

        if time_window.window_type == ForecastingWindow.ONE_MONTH or total_days <= 35:
            # Partition into 4 weekly intervals
            current_start = start_date
            for i in range(1, 5):
                if i == 4:
                    intervals_data.append((current_start, end_date, f"Week {i}"))
                else:
                    current_end = current_start + datetime.timedelta(days=6)
                    intervals_data.append((current_start, current_end, f"Week {i}"))
                    current_start = current_end + datetime.timedelta(days=1)
        else:
            # Partition into monthly intervals
            current_start = start_date
            month_idx = 1
            while current_start < end_date:
                # Step approximately one month (30 days)
                year = current_start.year
                month = current_start.month + 1
                if month > 12:
                    month = 1
                    year += 1

                try:
                    next_month_start = datetime.date(year, month, current_start.day)
                except ValueError:
                    # fallback to 30 days step
                    next_month_start = current_start + datetime.timedelta(days=30)

                current_end = next_month_start - datetime.timedelta(days=1)

                if current_end >= end_date or (end_date - current_start).days <= 35:
                    intervals_data.append((current_start, end_date, f"Month {month_idx}"))
                    break
                else:
                    intervals_data.append((current_start, current_end, f"Month {month_idx}"))
                    current_start = next_month_start
                    month_idx += 1

        # Associate active signals with each interval
        intervals: list[TimelineInterval] = []
        for interval_start, interval_end, label in intervals_data:
            active_sigs = [
                sig for sig in signals
                if self.is_signal_active_in_interval(sig, interval_start, interval_end)
            ]
            intervals.append(
                TimelineInterval(
                    start_date=interval_start,
                    end_date=interval_end,
                    label=label,
                    active_signals=active_sigs,
                )
            )

        return TimelineForecast(
            intervals=intervals,
            total_intervals=len(intervals),
        )
