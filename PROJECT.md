# garmin-agent

A bidirectional Garmin agent: pull activity/health data **out** of Garmin Connect
and push training plans/workouts **into** it from other sources.

This project is a fork of [`Taxuspt/garmin_mcp`](https://github.com/Taxuspt/garmin_mcp)
(MIT), which we build on top of. The upstream README (`README.md`) remains the
reference for the full tool catalogue and client configuration.

## Why this base was chosen

Web research (Oct 2026) compared every maintained Garmin MCP server. Context: in
**March 2026 Garmin added Cloudflare TLS fingerprinting**, which broke the old
`garth`/`requests` auth path. Surviving servers either ride the mobile-SSO +
TLS-impersonation flow in `python-garminconnect`, or drive a headless browser.

| Candidate | Stars | Download | Upload / schedule | Auth | Notes |
|---|---|---|---|---|---|
| **Taxuspt/garmin_mcp** | **1,309** | ✅ | ✅ upload + schedule + builders | mobile SSO, MFA, token store | **chosen** |
| cyberjunky/python-garminconnect (library) | 3,106 | ✅ | ✅ typed workout models | mobile SSO + `curl_cffi` | the engine underneath |
| Nicolasvegam/garmin-connect-mcp | 183 | ✅ | ⚠️ read-only | email/password | TS, no license |
| etweisberg/garmin-connect-mcp | 44 | ✅ | ✅ | headless Playwright | cookies expire in hours, AGPL |
| eddmann/garmin-connect-mcp | 64 | ✅ | ⚠️ partial | token store | stale since May 2026 |
| charlesfrisbee/garmin-workouts-mcp | 2 | ❌ | ✅ | tokens expire ~5 min | upload-only |
| wklm/garmin-workouts-mcp | 4 | ❌ | ✅ | — | upload-only, depends on the above |
| Garmin Chat Connector (official, hosted) | — | ✅ | ❌ read-only | hosted URL | no upload path |

Rationale for `Taxuspt/garmin_mcp`: the only option that is simultaneously
**bidirectional**, **actively maintained** (pushed 2026-10-01), **MIT** licensed,
and **trivial to run** (`uvx`, one-time auth, ~6-month tokens, no browser
automation).

## Architecture

```
MCP client (Claude / Codex / Inspector)
        │  stdio or streamable-http
        ▼
src/garmin_mcp/__init__.py      # FastMCP app, tool filtering, transport config
        │  configure(garmin_client)
        ▼
per-domain modules (register_tools):
  activity_management  health_wellness  training      workouts
  workout_builders     activity_analysis courses      calendar_events
  nutrition            devices          gear_management …
        │
        ▼
python-garminconnect (mobile SSO + curl_cffi TLS impersonation)
        │
        ▼
connect.garmin.com  /  gc-api
```

## Bidirectional capability (verified)

Confirmed by an actual MCP handshake, not just by reading docs:

```
$ uv run python scripts/probe_mcp.py
server: Garmin Connect v1.0 1.28.1
tools registered: 153

  [x] download  get_activities
  [x] download  get_activity
  [x] download  download_activity_file
  [x] upload    upload_workout
  [x] upload    upload_workouts
  [x] schedule  schedule_workout
  [x] schedule  schedule_workouts
  [x] schedule  schedule_week
```

- **Outbound (from Garmin):** activity summaries and details, splits, HR zones,
  GPS/polyline, FIT/GPX/TCX/CSV file downloads, sleep, HRV, Body Battery,
  training status/readiness, VO2 max, weight, gear, nutrition.
- **Inbound (to Garmin):** `upload_workout` / `upload_workouts`, high-level
  builders (`create_run_workout`, `create_run_interval_workout`,
  `create_walk_run_workout`, `create_strength_workout`), and calendar placement
  via `schedule_workout` / `schedule_workouts` / `schedule_week`.

## Setup

```bash
uv sync                       # installs Python toolchain + deps
```

### Authenticate once (required, manual — needs real Garmin credentials)

```bash
uv run garmin-mcp-auth        # prompts for email, password, and MFA if enabled
```

Tokens are written to `~/.garminconnect` (mode 0600) and last ~6 months. The
server needs **no credentials in its config** afterwards. Do not put the Garmin
password in shell history or a committed file.

Run the server:

```bash
uv run garmin-mcp                                  # stdio (default)
GARMIN_MCP_TRANSPORT=streamable-http uv run garmin-mcp   # HTTP on :8000/mcp
```

## Verification

```bash
uv run pytest tests/unit -q          # 186 passed
uv run python scripts/probe_mcp.py   # handshake + tool inventory
```

`scripts/probe_mcp.py` needs no credentials: it opens the stdio handshake and
asserts the bidirectional tools are registered.

## Roadmap / where to extend

1. **Training-plan import.** A tool that ingests an external plan (Intervals.icu,
   TrainingPeaks, markdown/CSV) and fans it out to `upload_workout` +
   `schedule_workout`. Upstream intentionally omits sport-specific upload
   endpoints, so generic `upload_workout` is the entry point.
2. **Round-trip reconciliation.** Compare planned vs. completed activities and
   report compliance/adherence.
3. **Restrict write tools** on shared/delegated accounts with
   `GARMIN_ENABLED_TOOLS` to make them read-only.
4. **Keep upstream mergeable.** Isolate new tools in their own module so
   `git merge upstream/main` stays clean.

## Legal

Unofficial, not affiliated with Garmin. Uses Garmin's web services via the
community library. Personal use; respect Garmin's terms of service.
