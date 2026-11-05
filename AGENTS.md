# Reliable Gateway Agent Instructions

## Source of truth

Read `RELIABLE_GATEWAY_SPEC_FINAL_PYTHON.md` before planning or changing this
repository. It defines the API contract, invariants, milestone order, acceptance
gates, and explicit non-goals. Do not weaken or reinterpret its requirements to
make an implementation easier.

The purpose of this repository is incremental learning. Completing later work
early is a defect, not a bonus.

## Scope lock: do not implement the whole specification

1. Before making changes, identify the active stage from repository evidence.
   The active stage is the earliest stage whose acceptance gate is not fully
   satisfied, in this order:
   - Day 1 bootstrap
   - Milestone 1
   - Milestone 2
   - Milestone 3
   - Milestone 4
   - Milestone 5
   - Milestone 6
   - Milestone 7 (optional and only after Milestone 6)
2. State the active stage and the exact requested slice before implementation.
3. Implement only the user's requested work within that stage. A request such
   as "continue", "build the gateway", or "work on the project" means advance
   the active stage only; it does not authorize later milestones.
4. Do not start the next stage merely because the current change is complete.
   Stop after verifying the requested slice and report the remaining acceptance
   items.
5. Cross a milestone boundary only when:
   - the current gate has evidence that it passes; and
   - the user explicitly asks to begin or implement the next milestone.
6. If a request mixes stages, separate the work by milestone and ask the user
   which stage to do now. Small prerequisite fixes needed to verify the active
   stage are allowed; later-stage feature work is not.
7. Never add speculative abstractions, dependencies, configuration, deployment
   files, or observability hooks for a future milestone.

Repository structure in the specification describes the eventual project, not
what should be created immediately. Create files only when the active stage
requires them.

## How to determine progress

Use code, tests, runnable behavior, docs, and saved evidence—not directory names
or optimistic comments—to decide whether a gate is complete. Treat unchecked or
untested behavior as incomplete. If the evidence is ambiguous, remain on the
earlier stage and say what is missing.

At the start of a task, summarize:

```text
Active stage: <Day 1 or M1-M7>
Requested slice: <specific work>
Out of scope: <later capabilities that must not be added>
Gate evidence to produce: <tests/commands/docs>
```

## Task and progress tracker

Source: [project specification](RELIABLE_GATEWAY_SPEC_FINAL_PYTHON.md), Day 1,
sections 1–5, and milestone acceptance gates. This checklist is a navigation aid;
the specification remains authoritative for exact contracts and invariants.
Listing future work here does not authorize implementing it.

Use `[x]` only with code, test, command output, or document evidence. An unchecked
item may be unimplemented, partially implemented, or awaiting verification.
Build completion alone does not satisfy an acceptance gate. When updating this
tracker, record the date, commands/results and evidence paths; do not advance
stages automatically. Commits/tags remain manual tasks requiring an explicit
user request, even where the guide suggests them.

### Current evidence — 5 November 2026

- Calendar progress: **Day 2**. Calendar days and acceptance stages are separate;
  the Day 1 bootstrap stage remains active until its outstanding checks pass.
- Active stage: **Day 1 bootstrap**; gate incomplete.
- `.venv/bin/pytest -q`: **48 passed** (0.45s) in the pre-commit check;
  8 backend cases and 40 gateway cases in `tests/unit/`. Gateway tests use
  mocked upstream HTTP and do not prove real-network behavior.
- `.venv/bin/ruff check .` and `.venv/bin/mypy src`: **passed**.
- `.venv/bin/ruff format --check .`: **passed**, 13 files already formatted;
  the previously reported backend formatting failures are resolved.
- User-verified in this conversation: all three services run and 20 real
  gateway requests alternate A/B; backend startup and clean Ctrl+C shutdown;
  request-ID propagation, invalid query 400, backend 503 pass-through, and 502
  when a backend is stopped. Exact commands/output were not supplied; no
  terminal transcript is saved yet. Worker counts were not explicitly recorded.
- Backend delay/timeout timing and invalid-ID replacement remain untested in
  the backend suite; invalid-ID replacement is tested separately at the gateway.
- `docs/day1-notes.md` explains all four required concepts. Only the initial
  commit was present in the initial audit; project files were untracked. Backend B
  and basic gateway forwarding now exist, but do not establish M1 completion.

### Day 1 bootstrap — first backend (90–120 minutes)

Build and learning tasks:

- [x] Create the installable `src/reliable_gateway` project with `pyproject.toml`,
  `uv.lock`, `.python-version` (3.12), runtime dependencies and dev tools.
- [ ] Record successful Python and pytest version commands for the local toolchain.
- [x] Add backend factory `create_app(backend_id: str) -> FastAPI` and backend A
  Uvicorn entry point (`reliable_gateway.backend.backend_a:app` in this repo).
- [x] Implement `/healthz` and normal `/v1/work` JSON with backend identity.
- [x] Validate `delay_ms` (integer 0–2000) and `fail` (`none|503|timeout`),
  defaults included; invalid inputs return 400 `invalid_parameter` with ID.
- [x] Implement supplied printable ASCII request IDs (nonempty, <=128 chars),
  UUID fallback, and matching response header/JSON IDs.
- [ ] Verify rejected request IDs (empty, nonprintable, non-ASCII, >128 chars)
  generate UUIDs; currently only missing-header generation is tested.
- [ ] Verify async normal delay, immediate simulated 503, and 3s timeout-mode
  success; delay/timeout code is present but timing behavior is untested.
- [x] Write at least the four specified deterministic backend tests.
- [x] Explain Uvicorn, ASGI, event loop, and HTTPX in `docs/day1-notes.md`.

Acceptance and evidence:

- [x] Start backend A with Uvicorn and stop cleanly with Ctrl+C
  (user-verified in conversation; startup command/bind transcript not saved).
- [ ] Save curl results for health, `delay_ms=20`, `fail=503`, and `delay_ms=-1`;
  confirm expected statuses, bodies and matching request IDs over HTTP.
- [x] Run pytest successfully (48 cases pass; see dated evidence above).
- [x] Run Ruff lint successfully.
- [x] Run Ruff format check successfully (13 files; pre-commit verification).
- [ ] When explicitly requested, commit Day 1 with the guide's suggested message
  `day1: backend service and API contract tests`.

### M1 — working gateway and local environment (6 hours)

Build tasks (spec sections 1–3 and M1; exclude M2+ behaviors):

- [ ] Run two independent backend services with identities A/B, one worker each.
- [ ] Add gateway factory and concurrency-safe initial round-robin routing.
- [x] Validate GET queries at gateway before forwarding; preserve upstream
  status/JSON including 503, map transport failures to 502 `upstream_error`.
- [ ] Validate/generate/propagate request IDs; emit `X-Backend-ID` for selected
  backend responses and correlate request ID in gateway logs/backend response.
- [ ] Forward only controlled `Content-Type`/`X-Request-ID` headers; never
  blindly forward arbitrary or hop-by-hop headers.
- [ ] Own exactly one HTTPX AsyncClient per gateway process in lifespan; set
  explicit pool limits, keepalive expiry and timeouts; close client/responses.
- [ ] Parse/validate relevant environment configuration at startup; disable
  hidden client/intermediary retries and keep runtime I/O asynchronous.
- [ ] Add basic gateway management health endpoints on :9090 and backend
  `/healthz`, without active health-aware routing.
- [ ] Provide development-only backend `POST /_admin/state` fault controls:
  `healthy`, `fixed_delay_ms` (0–3000), `failure_rate` (0–1), seeded in tests;
  keep admin inaccessible through gateway and reject accidental public binding.
- [ ] Package gateway :8080, management :9090 and two backends in Compose;
  expose backends only on loopback if inspection needs host ports.
- [ ] Provide local scripts/tooling, setup README linking the spec, architecture
  sketch, and `make up`, `down`, `test`, `check` with failure propagation.
- [ ] Make `test` run pytest unit/integration tests and `check` run Ruff lint,
  Ruff format check, static checker, and pytest.

Acceptance and evidence:

- [x] Real gateway GET returns valid 200 JSON (user-verified).
- [x] Prove 20 sequential real GETs alternate A/B (user-verified).
- [ ] Record one Uvicorn worker per service for the real routing verification.
- [x] Prove `delay_ms=99999` returns 400 without contacting a backend
  (mock-upstream test; user also verified invalid-query 400 over real HTTP).
- [ ] Prove request ID matches gateway logs and backend response.
- [ ] Pass deterministic unit/integration tests and full `make check`.
- [ ] Save terminal output/screenshot and short architecture sketch; create
  guide's `m1-basic-routing` commit only when explicitly requested.

### M2 — deadlines, retries, cancellation and POST safety (7 hours)

Build tasks:

- [ ] Enforce monotonic 1000ms total budget including routing, attempts/backoff;
  each attempt gets min(remaining budget, 400ms).
- [ ] Retry GET only for transport error, timeout or HTTP 503, at most two
  attempts total when time remains; never retry 400/401/403/404/429 or POST.
- [ ] Add cancelable exponential full-jitter backoff (default [0, 50ms] before
  attempt 2), never sleeping past the total deadline.
- [ ] Emit `X-Gateway-Attempts`; return 504 `upstream_timeout` on deadline,
  502 `upstream_error` on non-timeout transport failure, retain final HTTP 503.
- [ ] Add backend/gateway `POST /v1/operations`: validate JSON and nonempty
  printable ASCII `operation_id` <=64 chars; invalid input returns 400.
- [ ] Deduplicate per backend: first execution 201, repeat 200 with same body
  and `applied_count: 1`; gateway makes one attempt only.
- [ ] Detect real client disconnects; cancel/await outbound and watcher tasks,
  interrupt backoff, close responses/connections, preserve CancelledError.

Acceptance and evidence:

- [ ] First backend 503, second 200: GET succeeds within two total attempts.
- [ ] Both backends slow: 504 within 1000ms + 100ms scheduling tolerance.
- [ ] Transient POST failure results in exactly one gateway attempt.
- [ ] Same-backend duplicate operation does not increment counter twice.
- [ ] Cancel 100 real-network requests midflight; compare tasks/connections
  before/after cleanup grace and prove no growth, leaks or hanging requests.
- [ ] Save test-case/observed-attempt table and deliberate unsafe-retry example;
  document cross-backend deduplication limitations in `docs/tradeoffs.md`.
- [ ] Run full `make check` and required real-Uvicorn cancellation tests.

### M3 — health-aware routing and overload protection (6 hours)

Build tasks:

- [ ] Lifespan-owned health polling every 1000ms with 200ms timeout; remove
  after 2 consecutive failures, restore after 2 consecutive successes.
- [ ] Route round-robin only among eligible backends; prefer a different
  backend on retry without assuming it is healthy.
- [ ] Separate `/livez` (event loop alive, no backend check) from `/readyz`
  (startup/config complete and at least one eligible backend).
- [ ] Reject with 503 `no_healthy_backend` when no backend is eligible.
- [ ] Add non-waiting atomic admission capped at 100 requests per process,
  including retry/backoff; reject with 503 `overloaded`, release in finally.
- [ ] Protect selector/health/admission shared state across awaits; cancel and
  await health tasks at shutdown; document process-local state in tradeoffs.

Acceptance and evidence:

- [ ] Unhealthy B stops receiving new traffic within 3s; successes go to A.
- [ ] Restored B becomes eligible within 3s.
- [ ] Both unhealthy: readiness 503 and gateway 503 `no_healthy_backend`.
- [ ] >100 concurrent blocked requests: excess rejected promptly (local target
  <100ms excluding host overload); admitted requests never exceed 100.
- [ ] Hundreds of concurrent requests/health transitions preserve consistent
  state; test two independent gateway processes to prove process-local limits.
- [ ] Save B removal/recovery timeline, test output and full `make check`.

### M4 — observability, performance and failure experiments (8 hours)

Build tasks:

- [ ] Instrument ASGI/FastAPI and HTTPX with gateway inbound, attempt child,
  and backend spans; propagate W3C trace context correctly across async tasks.
- [ ] Provision Collector, Jaeger, Prometheus and Grafana in local deployment.
- [ ] Expose :9090 `/metrics`: `gateway_requests_total{route,method,status_class}`,
  `gateway_request_duration_seconds{route,method}` histogram,
  `gateway_upstream_attempts_total{backend,outcome}`, `gateway_inflight_requests`,
  `gateway_backend_healthy{backend}`, and `gateway_rejected_total{reason}`.
- [ ] Keep all labels bounded; exclude request/trace/operation IDs and arbitrary
  paths; structured logs include ID, backend, duration, status and attempts,
  without payloads or credentials.
- [ ] Commit dashboard definitions for request rate, p50/p95/p99, 5xx fraction,
  inflight, rejections and backend health (commit only on explicit request).
- [ ] Write k6 smoke: 5 VUs for 30s with correctness assertions.
- [ ] Write k6 normal: arrival-rate 50 RPS for 2 minutes, delay 20ms, fail none.
- [ ] Write k6 degraded: 50 RPS for 2 minutes, B fixed 900ms or unhealthy, A 20ms.
- [ ] Write overload experiment: 200 concurrent slow requests, bounded inflight
  and explicit rejections; add `make smoke`, `load`, `fault`, `observe` tooling.
- [ ] Encode pass criteria as failing k6 thresholds, with failures propagated.

Acceptance and evidence:

- [ ] Every gateway request has correlated trace/log context identifying attempts.
- [ ] Dashboard reveals B failure without filtering by unique request IDs.
- [ ] Normal: success >=99%, p95 <250ms locally; if missed, leave gate visibly
  unmet and record environment/root cause rather than conceal failure.
- [ ] Degraded: bounded retries, stable memory, <=100 active requests, and
  accurate error/rejection metrics; overload verifies admission bound.
- [ ] Save k6 JSON results and before/after graphs; write `docs/benchmarks.md`
  with actual numbers, bottlenecks, environment and variability.
- [ ] Run full `make check` and all four load profiles; retain threshold exits.

### M5 — containers, Kubernetes and safe rollout (6 hours)

Build tasks:

- [ ] Pin Python/container versions (no latest), use minimal images/non-root user.
- [ ] Add kind Deployments, Services, ConfigMap, resources and probes;
  at least two gateway pods, one Uvicorn worker per pod.
- [ ] Add documented `make kind-up`/`kind-down` commands (destructive execution
  still requires explicit user authorization).
- [ ] On SIGTERM promptly fail readiness, stop new traffic, drain inflight work
  up to 5s; align Uvicorn timeout and Kubernetes termination grace.
- [ ] Prepare normal v1→v2 rollout, intentional broken config/upstream rollout,
  and rollback procedure.

Acceptance and evidence:

- [ ] Prove SIGTERM drain/shutdown via real subprocess/signal tests.
- [ ] Normal `kubectl rollout status` succeeds.
- [ ] Broken v2 blocked by readiness/rollout conditions; record whether v1
  remains serviceable and any observed failures.
- [ ] Rollback restores working version and passing smoke test.
- [ ] Kill gateway pod: surviving replica serves new requests; record transients.
- [ ] Save manifests, commands/logs, deployment/runbook notes and observed
  liveness/readiness explanation; run full `make check`.

### M6 — production game day and write-up (4–8 hours)

- [ ] Run normal 50 RPS traffic, then simultaneously introduce B latency of
  900ms and accidental retry/concurrency configuration increase; record actual
  behavior without leaving hidden/unbounded retries in the implementation.
- [ ] Detect first user-visible dashboard symptom; record timestamps/impact.
- [ ] Diagnose spans, failing backend, attempt counts and saturation/rejections.
- [ ] Mitigate by restoring retry bounds and taking B out of service; verify
  impact reduction with measurements.
- [ ] Recover B safely and verify balanced routing.
- [ ] Rank 2–3 prevention changes by expected impact and implementation cost.
- [ ] Write `docs/incident-report.md`: timeline, impact, detection, contributing
  factors, mitigation and follow-ups without blame or invented observations.
- [ ] Complete `docs/tradeoffs.md`: retry safety, backend-local idempotency,
  process-local state, health-check lag and inflight bound rationale.
- [ ] Verify `docs/runbook.md` diagnosis/recovery commands work.
- [ ] Verify README clean-room setup by someone unfamiliar with the code.
- [ ] Produce final PR-style description with real benchmark numbers,
  screenshots and test-result links; run full `make check`.

### M7 — optional durable parent/child workflows (6–10 hours; only after M6)

Build tasks:

- [ ] Obtain explicit opt-in after M6; create separate workflow service on
  loopback :8090, keeping existing gateway routes unchanged.
- [ ] Add `POST /v1/sessions`: nonempty title <=120 chars, 201 UUID/title/active.
- [ ] Add `POST /v1/sessions/{id}/children`: simulate payload per spec, 202 queued;
  same parent/task_key and payload returns same child ID without rescheduling,
  mismatched payload returns 409.
- [ ] Add session GET with child ID/key/status/result/error in creation order.
- [ ] Add immediate-return 202 `/run`, start queued children once even when
  concurrent runs race; maximum 4 executing tasks across the service process.
- [ ] Add 202 `/cancel` for pending/running children; terminal states immutable;
  missing sessions 404, malformed inputs 400, conflicting operations 409.
- [ ] Persist parents, children, fingerprints, attempts, timestamps and status
  in SQLite; commit before acceptance/completion, no transaction across await.
- [ ] Transactionally enforce queued→running→succeeded|failed|cancelled and
  queued→cancelled, updated_at and increasing transition sequences; never
  silently convert unknown status to success.
- [ ] Use TaskGroup inside bounded batches and Semaphore(4); record ordinary
  child failures for isolation, distinguish unhandled fail-fast behavior.
- [ ] Track lifespan-owned session runners; cancel/release/await on shutdown;
  cooperative cancellation reaches sleeps and persists terminal state.
- [ ] At startup recover running→queued, rerun only on next `/run`; document
  at-least-once replay and destination idempotency needed for real side effects.
- [ ] Log parent/child/correlation IDs and transitions, add useful spans,
  exclude high-cardinality metric labels.

Acceptance and evidence:

- [ ] Three children yield distinct results and correct parent associations.
- [ ] Three 300ms children finish significantly faster than ~900ms sequential;
  record timings with generous tolerance on a nonoverloaded runtime.
- [ ] Duplicate key starts one child; mismatched duplicate returns 409.
- [ ] Isolated child failure permits sibling success; separate unhandled
  TaskGroup exception test proves sibling cancellation.
- [ ] Cancelling A leaves parent B's children unaffected.
- [ ] SIGKILL live server midwork, restart, verify queued recovery and rerun to
  terminal state; preserve real crash/restart transcript (not SIGTERM).
- [ ] Two concurrent `/run` calls cannot claim/start the same child twice.
- [ ] Write `docs/child-workflows.md`: parent/child model, tasks vs OS threads
  vs processes, transitions, replay/failure semantics and single-process SQLite
  limits (no distributed coordination, HA or exactly-once claim).
- [ ] Save tests, concurrent-work timeline, crash transcript and one-page
  design note; run full `make check`.

## Stage boundaries

### Day 1 bootstrap

Implement only backend A and its initial contract: `/healthz`, `/v1/work`,
validated query parameters, request-ID validation/generation/propagation,
simulated delay/503/timeout behavior, at least the four specified tests, and
`docs/day1-notes.md`. Verify Uvicorn startup, pytest, Ruff check, and Ruff format.

Do not add backend B, a gateway, round-robin routing, retries, active health
routing, Docker/Compose, telemetry, Kubernetes, or workflows.

### Milestone 1: working gateway and local environment

Add backend B, the stable external contract, initial round-robin gateway,
request-ID propagation, one lifespan-owned HTTPX client per gateway process,
basic health endpoints, deterministic unit/integration tests, Docker Compose,
and the required local tooling/documentation.

Do not add retries, deadline policy, cancellation machinery, POST operation
deduplication, active health-based routing, overload protection, telemetry,
load testing, Kubernetes, or workflows. Health endpoints in M1 do not authorize
M3 health-aware selection.

### Milestone 2: deadlines, retries, cancellation, and POST safety

Add the total and per-attempt deadlines, bounded GET-only retry policy with
cancelable jitter, request-attempt reporting, disconnect cancellation, and
`POST /v1/operations` with backend-local deduplication and no gateway retries.
Prove timing, attempt count, cancellation cleanup, and POST safety over the
appropriate in-process and real-network tests.

Do not add active health polling/selection, inflight admission limits,
OpenTelemetry/metrics/dashboards, Kubernetes, or workflows.

### Milestone 3: health-aware routing and overload protection

Add periodic health checks with failure/success thresholds, eligible-backend
selection and recovery, retry preference for a different backend, separate
liveness/readiness semantics, and non-waiting per-process admission capped at
100 inflight requests. Prove concurrency safety and document process-local
state using single- and two-gateway-process tests.

Do not add milestone 4 telemetry/load infrastructure, Kubernetes, game-day
artifacts, or workflows.

### Milestone 4: observability, performance, and failure experiments

Add bounded-cardinality Prometheus metrics, structured logs, OpenTelemetry
ASGI/HTTPX tracing, collector/Jaeger/Prometheus/Grafana configuration, committed
dashboard(s), and the specified k6 smoke, normal, degraded, and overload tests.
Preserve the exact load profiles and make thresholds fail commands. Record
honest local results and variability in `docs/benchmarks.md`.

Do not add Kubernetes rollout machinery, perform the M6 game day, or add
workflows.

### Milestone 5: containers, Kubernetes, and safe rollout

Add pinned/minimal non-root images, local kind manifests, resources and probes,
one Uvicorn worker per pod, graceful termination behavior, horizontal gateway
replicas, and documented normal/broken rollout and recovery evidence.

Do not pre-write the M6 incident conclusions or add M7 workflows.

### Milestone 6: production game day and write-up

Run the specified simultaneous latency/configuration incident. Use actual
observations to produce the incident timeline, impact, diagnosis, mitigation,
recovery, ranked prevention work, tradeoffs, runbook, and clean-room README.
Do not invent evidence, benchmark numbers, traces, or screenshots.

Do not add M7 unless the user explicitly opts into it after M6.

### Milestone 7: optional durable parent/child workflows

Treat this as a separate workflow service, not a gateway rewrite. Add the
specified session/child API, SQLite state machine and transactional transitions,
bounded structured concurrency, tracked lifespan-owned runners, cancellation,
crash recovery, observability, tests, and `docs/child-workflows.md`.

Do not claim distributed coordination, high availability, exactly-once
execution, or durability beyond the specification's single-process SQLite
learning model.

## Invariants that apply whenever their feature exists

- Preserve the external API contract; invalid specified inputs return 400, not
  FastAPI's default 422.
- Use async I/O in request handlers. Do not use `requests`, `time.sleep`, or
  CPU-bound blocking work on the event loop.
- Initialize network clients and background tasks through FastAPI lifespan;
  close/cancel/await them during shutdown. Never create an HTTPX client per
  request or initialize it at module import time.
- Do not swallow `asyncio.CancelledError`. Explicitly clean up tasks, responses,
  connections, and admission counters in `finally` paths.
- Keep each service to one Uvicorn worker. Treat counters, fault state, routing,
  health, admission, and local idempotency as process-local.
- Forward only the controlled header subset. Never blindly proxy hop-by-hop or
  arbitrary client headers.
- Never add hidden or unlimited retries. Once M2 exists: at most two total GET
  attempts, one POST attempt, and the total request budget includes attempts,
  routing, and backoff.
- Once M4 exists, never use request IDs, trace IDs, operation IDs, or arbitrary
  paths as metric labels, and do not log payloads or credentials.
- Admin fault controls remain development/test-only and must not be exposed by
  the gateway or a public bind.
- Do not expose this educational gateway to the public internet or describe it
  as production-ready.

## Verification and evidence

Run the narrowest relevant tests during development, then the active stage's
full gate before claiming completion. `make check` must eventually be equivalent
to Ruff lint, Ruff format check, static type checking, and pytest, with failures
propagated. Use real Uvicorn/subprocess/network tests where the specification
requires real disconnect, signal, multi-process, or crash behavior; do not claim
that `httpx.ASGITransport` proves those behaviors.

Timing tests need explicit tolerances and should distinguish correctness from
performance. Never conceal a failed threshold or fabricate execution evidence.

At handoff, report:

- what changed within the active stage;
- commands run and their actual results;
- which acceptance items now pass;
- which items remain before the stage gate is complete; and
- confirmation that no later-stage features were introduced.

Do not commit, tag, publish, create cloud resources, or run destructive
environment operations unless the user explicitly requests them.
