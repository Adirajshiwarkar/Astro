import datetime
from zoneinfo import ZoneInfo


def local_to_utc(
    date_of_birth: datetime.date,
    birth_time: datetime.time,
    timezone_str: str,
) -> tuple[datetime.datetime, bool]:
    """Convert a local date, time, and timezone to an aware UTC datetime and a DST active flag.

    ZoneInfo is used to deterministically resolve offsets and DST transitions.
    """
    try:
        tz = ZoneInfo(timezone_str)
    except Exception as e:
        raise ValueError(f"Invalid or unsupported timezone: {timezone_str}") from e

    # Combine into naive datetime
    local_dt = datetime.datetime.combine(date_of_birth, birth_time)

    # Make the datetime timezone-aware using ZoneInfo
    aware_dt = local_dt.replace(tzinfo=tz)

    # Convert to UTC
    utc_dt = aware_dt.astimezone(datetime.UTC)

    # Check if Daylight Saving Time (DST) was active
    dst_offset = aware_dt.dst()
    is_dst = dst_offset is not None and dst_offset != datetime.timedelta(0)

    return utc_dt, is_dst
