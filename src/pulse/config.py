import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    app_port: int = int(os.environ.get("APP_PORT", "8000"))
    db_path: Path = Path(os.environ.get("DB_PATH", "data/pulse.db"))
    check_timeout_seconds: float = float(os.environ.get("CHECK_TIMEOUT_SECONDS", "2.0"))
    degraded_latency_threshold_ms: int = int(os.environ.get("DEGRADED_LATENCY_THRESHOLD_MS", "1500"))
    failures_to_down: int = int(os.environ.get("FAILURES_TO_DOWN", "2"))
    recovery_successes: int = int(os.environ.get("RECOVERY_SUCCESSES", "2"))
    availability_window_hours: int = int(os.environ.get("AVAILABILITY_WINDOW_HOURS", "24"))
    default_slo_target: float = float(os.environ.get("DEFAULT_SLO_TARGET", "99.9"))
    webhook_url: str = os.environ.get("WEBHOOK_URL", "http://localhost:9900/")


settings = Settings()
