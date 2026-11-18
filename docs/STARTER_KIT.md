# STARTER_KIT — recon of the supplied kit

Reconnaissance of the supplied starter kit (pulse-starter-kit). Units 0, 1 and 6 read this file.

## Services (mock, supplied)
| Name | Compose hostname | Internal port | Host port | Health endpoint | Control endpoints |
|---|---|---|---|---|---|
| quotes | quotes | 8080 | 7001 | http://localhost:7001/health (internal: http://quotes:8080/health) | /control/down, /control/slow?ms=, /control/flaky?rate=, /control/reset |
| payments | payments | 8080 | 7002 | http://localhost:7002/health (internal: http://payments:8080/health) | same |
| claims | claims | 8080 | 7003 | http://localhost:7003/health (internal: http://claims:8080/health) | same |
| notifications | notifications | 8080 | 7004 | http://localhost:7004/health (internal: http://notifications:8080/health) | same |

Verify exact control endpoints:
- `POST /control/down` -> Health checks return 503 until reset
- `POST /control/slow?ms=3000` -> Health checks succeed after `ms` delay
- `POST /control/flaky?rate=0.3` -> Health checks fail with 500 at random rate
- `POST /control/reset` -> Back to normal (200 OK)
- `GET /control/state` -> Returns current mode JSON

## Compose
- Network name: `pulse-starter-kit_default` (or shared compose network)
- Compose file location: `pulse-starter-kit/docker-compose.yml`
- How Pulse joins the network: joins external network `pulse-starter-kit_default` or defined together in docker-compose.yml

## Webhook receiver
- Hostname and port: `webhook-receiver:9000` (host: `localhost:9900` or env `WEBHOOK_PORT`)
- URL path: `/` (or any path, e.g. `/webhook`)
- Auth (header/token/none): none
- Expected payload shape:
```json
{
  "event": "incident_opened",
  "incident_id": 1,
  "service": "payments",
  "state": "DOWN",
  "opened_at": "2026-11-18T12:00:00Z",
  "message": "Service payments has entered DOWN state after 2 consecutive failures"
}
```
- Events it understands: Accepts any valid JSON POST to any path.
- Where received events can be viewed: `http://localhost:9900/` (live HTML table) and `http://localhost:9900/api/received` (JSON list). Clear with `DELETE /api/received`.

## Drill script
- Location and command: `pulse-starter-kit/scripts/incident-drill.sh`
- Commands:
  - `bash scripts/incident-drill.sh` (full 7-minute drill, 60s step)
  - `bash scripts/incident-drill.sh --fast` (short drill, 20s step)
  - `bash scripts/incident-drill.sh --reset` (reset all services to normal)
- Schedule of events it triggers:
  1. Claims down (2 units)
  2. Claims reset (1 unit)
  3. Payments slow (3s) (1 unit)
  4. Payments reset (1 unit)
  5. Quotes flaky (50% errors) (2 units)
  6. Quotes reset

## Other
- Mock service returns internal error message on down: e.g. `"upstream quotes-db timeout at 10.12.4.7:5432"`. Per requirements, internal error messages must never leak onto public status pages!
