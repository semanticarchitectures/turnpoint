# Phase 3 demo: score two routes against one scenario

Walks through the Phase 3 exit criterion from `docs/PLAN.md`: *"Two agent
systems run one scenario and get comparable scores."* Two different
routes stand in for two agent systems' different tactics — a scorer that
gives them different, reproducible scores demonstrates the harness
works, without needing two actual independent agents. Everything here is
notional — synthetic coordinates, a synthetic elevation raster and a
notional threat, not a real place, system or threat (`AGENTS.md`).

## Tasking

> Plan a route from notional airfield ALPHA (0.5N, 0.05E) to notional
> airfield BRAVO (0.5N, 0.95E). There is a terrain feature between the
> two fields and a notional SAM (NOTIONAL-SAM-A) near the direct track.
> Clear the terrain by 500 ft, reach BRAVO within 15 minutes at 300 kt,
> and avoid the SAM's engagement envelope if you can.

The scenario file (`docs/specs/scenario-format.md`) encoding this is
generated below, not hand-written — see `make_scenario_data.py`.

## 0. One-time setup

```bash
pip install -e ".[dev]"
python scenarios/phase3-demo/make_scenario_data.py   # writes data/phase3-demo/
```

## 1. Two plans, two tactics

**Plan A ("direct-high"):** straight line at 15000 ft — the phase1-demo
playbook: climb to clear the hill, don't worry about anything else.

**Plan B ("diverted"):** a three-leg route at 5000 ft that swings north
through a waypoint at (0.9N, 0.5E) — low enough that altitude alone
doesn't matter, routed instead to stay outside the SAM's 10 nm
engagement ring entirely.

Start the API from the repo root:

```bash
turnpoint-api &   # or: uvicorn turnpoint.api.app:app --port 8123
```

Create both plans:

```bash
PLAN_A=$(curl -s -X POST http://127.0.0.1:8123/plans -H 'Content-Type: application/json' -d '{
  "name": "direct-high", "actor": "demo-agent-A",
  "turnpoints": [
    {"name": "ALPHA", "lat": 0.5, "lon": 0.05, "altitude_ft": 15000},
    {"name": "BRAVO", "lat": 0.5, "lon": 0.95, "altitude_ft": 15000}
  ]}' | python3 -c "import sys,json;print(json.load(sys.stdin)['plan']['id'])")

PLAN_B=$(curl -s -X POST http://127.0.0.1:8123/plans -H 'Content-Type: application/json' -d '{
  "name": "diverted", "actor": "demo-agent-B",
  "turnpoints": [
    {"name": "ALPHA", "lat": 0.5, "lon": 0.05, "altitude_ft": 5000},
    {"name": "DETOUR", "lat": 0.9, "lon": 0.5, "altitude_ft": 5000},
    {"name": "BRAVO", "lat": 0.5, "lon": 0.95, "altitude_ft": 5000}
  ]}' | python3 -c "import sys,json;print(json.load(sys.stdin)['plan']['id'])")
```

## 2. Score both against the same scenario

```bash
curl -s "http://127.0.0.1:8123/plans/$PLAN_A/score?scenario=phase3-demo/scenario.json"
curl -s "http://127.0.0.1:8123/plans/$PLAN_B/score?scenario=phase3-demo/scenario.json"
```

(`scenario` is a filename resolved under `data/`, same as `nasr_source`;
the actual `dted_source` inside the scenario file is used the same way
every other `dted_source` argument is — decision 0013.)

Over MCP the same file scores the same way:

```
score_plan(plan_id="<PLAN_A>", scenario_path="data/phase3-demo/scenario.json")
```

## Expected result

| | Plan A (direct-high) | Plan B (diverted) |
| --- | --- | --- |
| Terrain clear | yes | yes |
| SAM-1 exposed | **yes** | no |
| ete_min | ~10.8 | ~14.4 |
| within_target_time (11 min) | yes | **no** |
| within_max_time (15 min) | yes | yes |
| **score** | **85.0** | **~96.6** |

Both plans clear the terrain and reach BRAVO in time to avoid the hard
15-minute cap, so neither fails outright (`reached_objective: true` for
both). Plan A is fast but flies straight through the SAM's engagement
ring — a fixed 15-point exposure penalty. Plan B avoids the SAM
entirely but takes longer than the 11-minute target, costing it a
smaller, proportional late-arrival penalty. Different tactics, two
different but comparable, reproducible scores — exactly what a scorer
for agent evaluation needs to do. `airspace_checked` is `false` in both
reports: Turnpoint has no class-airspace overlay yet (decision 0013), so
neither score reflects it, and the report says so rather than staying
silent about it.

Re-running either score call, with the same scenario file and the same
plan, always returns the same numbers — no wall-clock time or randomness
anywhere in `turnpoint.scenario` (`AGENTS.md` section 6).
