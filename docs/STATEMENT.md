# Problem Statement: Option 1 — Pulse (Service Status and Incident Hub)

## The Problem
Modern distributed systems consist of numerous independent services. When failures, slowdowns, or flakiness occur, engineering teams, support staff, and customers need fast and transparent visibility:
- **Service owners / on-call engineers:** detect service failures rapidly, monitor latency, and coordinate incident response.
- **Support team:** understand immediately which services are impaired to communicate accurately with users.
- **Customers:** view a trustworthy, public, read-only status page without exposing internal infrastructure details or error logs.

## Core Capabilities Required
1. **Service Catalogue:** Register and manage services with HTTP health URLs, owner details, check intervals, and target SLOs.
2. **Health Check Prober:** Asynchronously probe services concurrently with robust timeouts so that one slow service never delays checks for others.
3. **State Classification & State Transitions:**
   - HEALTHY: HTTP 2xx and response time < 1.5s
   - DEGRADED: HTTP 2xx with latency >= 1.5s, or single failed check
   - DOWN: 2 consecutive failures
   - RECOVERY: 2 consecutive healthy checks (< 1.5s)
4. **Automated Incident Lifecycle:**
   - Automatically open an incident when a service is DOWN.
   - Enforce at most one active incident per service.
   - Allow operator acknowledgement and notes.
   - Automatically resolve the incident upon verified recovery.
5. **Real-time Notifications:** Webhook delivery on incident opened and incident resolved.
6. **Reliability Metrics:** Rolling 24-hour availability estimate, remaining error budget, MTTD (Mean Time to Detect), MTTR (Mean Time to Resolve), and checker performance (lag and duration).
7. **Dual-Audience Dashboards:**
   - Operator Dashboard (`/ops`): Live health status, latency, incident timeline, acknowledgement, notes, and service management.
   - Public Status Page (`/status`): Customer-facing, high-level status and incident history, strictly sanitised with zero data leaks (no health URLs, no owners, no internal stack traces).
