# Questions for the product owner

Status key: OPEN = not yet answered. ANSWERED = record the actual answer, who gave it and when.
"Default" is only a fallback from PLAN.md section 3. It is not an answer and not a decision.

| # | Question | Default if no answer is available | Status | Actual answer |
|---|---|---|---|---|
| Q1 | What response-time threshold separates healthy from degraded? | HTTP 2xx under 1.5 seconds is healthy; slower 2xx is degraded. | ANSWERED | HTTP 2xx under 1.5s healthy; >= 1.5s degraded (D-01). |
| Q2 | How many consecutive failures should open an incident? | Two consecutive failed checks; the first failure marks the service degraded. | ANSWERED | Two consecutive failures mark DOWN and open an incident; first marks DEGRADED (D-02). |
| Q3 | How many successful checks are needed to resolve an incident? | Two consecutive healthy checks. | ANSWERED | Two consecutive healthy checks (< 1.5s) resolve an incident (D-03). |
| Q4 | What availability window should the dashboard show? | Rolling 24 hours, labelled as a sampled estimate. | ANSWERED | Rolling 24 hours, labelled as sampled estimate (D-04). |
| Q5 | What SLO target should new services use? | 99.9%, editable per service. | ANSWERED | 99.9% default, editable per service (D-05). |
| Q6 | What webhook payload or authentication does the supplied receiver expect? | Inspect its README and send the smallest compatible JSON payload. | ANSWERED | Smallest JSON payload with incident and service metadata, no auth (D-06). |
| Q7 | Is it acceptable to extend the supplied Docker Compose setup? | Yes; keep the supplied mock services intact and add Pulse to the same runnable setup where practical. | ANSWERED | Yes, Pulse joins the starter kit network and exposes dashboard on port 8000 (D-07). |

## Additional questions to raise

| # | Question | Status | Actual answer |
|---|---|---|---|
| Q8 | What does "how the checking itself is performing" (must-have #9) mean? Lag and duration of checks, or something else? | ANSWERED | Check duration (ms) and check lag (difference between scheduled time and actual execution time) plus skipped runs counter. |
