-- Pulse Database Schema (SQLite)

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    health_url TEXT NOT NULL UNIQUE,
    owner TEXT NOT NULL,
    interval_seconds INTEGER NOT NULL DEFAULT 10,
    slo_target REAL NOT NULL DEFAULT 99.9,
    enabled INTEGER NOT NULL DEFAULT 1,
    current_state TEXT NOT NULL DEFAULT 'HEALTHY',
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    consecutive_successes INTEGER NOT NULL DEFAULT 0,
    first_failure_at TEXT,
    next_check_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS health_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    scheduled_at TEXT NOT NULL,
    started_at TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    http_status INTEGER,
    latency_ms INTEGER,
    state TEXT NOT NULL,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_health_checks_service_checked ON health_checks(service_id, checked_at);

CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    opened_at TEXT NOT NULL,
    resolved_at TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    acknowledged_at TEXT,
    acknowledged_by TEXT,
    title TEXT NOT NULL
);

-- Partial unique index enforcing exactly one active incident per service
CREATE UNIQUE INDEX IF NOT EXISTS idx_incidents_active_service 
ON incidents(service_id) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS incident_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_incident_events_incident_id ON incident_events(incident_id, created_at);

CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 1,
    outcome TEXT NOT NULL,
    response_code INTEGER,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
