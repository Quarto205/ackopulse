from datetime import datetime, timezone


class Clock:
    """Injectable UTC clock."""

    def __init__(self, fixed_time: datetime | None = None):
        self._fixed_time = fixed_time

    def now(self) -> datetime:
        if self._fixed_time is not None:
            return self._fixed_time
        return datetime.now(timezone.utc)

    def set_time(self, dt: datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        self._fixed_time = dt

    def advance(self, seconds: float):
        if self._fixed_time is None:
            self._fixed_time = datetime.now(timezone.utc)
        from datetime import timedelta
        self._fixed_time += timedelta(seconds=seconds)

    def reset(self):
        self._fixed_time = None


# Global default clock
clock = Clock()
