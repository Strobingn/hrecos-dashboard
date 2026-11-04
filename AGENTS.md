# AGENTS.md

Guidance for AI coding agents working in `Strobingn/hrecos-dashboard`. Read this before changing code. Where this file and a subproject README disagree, the README for that subproject wins for its own internals; this file wins for cross-cutting rules.

## What this repo is

A Hudson River monitoring system focused on the main stem from Tappan Zee / Piermont (south) to Poughkeepsie (north), centered on West Point / Cornwall-on-Hudson / Newburgh. It has several independent parts that share data contracts:

| Path | What it is | Language / stack |
| --- | --- | --- |
| `index.html`, `app.js`, `style.css`, `config.js`, `fish-sounds.js`, `manifest.json` | Static dashboard served by **GitHub Pages** | Vanilla JS, Leaflet + OSM |
| `backend/` | API: station data, tides, anomalies, alerts | Python 3.12, FastAPI, SQLAlchemy async, APScheduler |
| `frontend/` | Older nginx-served dashboard for the Docker stack | Static HTML (not what Pages serves) |
| `mobile/` | "HRECOS RiverWatch" Android app | Expo SDK 56, React Native 0.85, React 19 |
| `edge/` | Virtual hydrophone node (Raspberry Pi + Aquarian H2a target) | Python ≥3.11 package `hydrophone_node` |
| `edge/sonar/` | Synthetic sonar node + Lowrance `.sl2`/`.sl3` importer | Python packages `sonar_node`, `sonar` |
| `ml/` | Offline fish-sound classifier (Perch 2.0 embeddings + probe) | Python, numpy/scikit-learn/onnxruntime |
| `ml/sonar/` | Synthetic sonar-track classifier | Python, NumPy |
| `supabase/` | Migrations + seed for the fish acoustic / sonar network | Postgres, Supabase CLI 3 |
| `contracts/` | JSON Schemas for every row the edge/ML code writes | JSON Schema 2020-12 |
| `data/stations.json` | **Single source of truth** for the station registry | JSON |
| `docs/` | `fish-network.md`, `sonar-track.md` — the DB contracts in prose | Markdown |

## Setup and commands

Run commands from the directory shown. Each Python subproject has its own requirements; do not merge them.

### Backend

```bash
pip install -r backend/requirements.txt pytest pytest-asyncio
python -m pytest            # from repo root; uses root pytest.ini (backend/tests)
```

- Root `pytest.ini` deselects `live` and `network` markers by default. Do **not** remove that `addopts`.
- Live provider check (hits NOAA, USGS, NDBC, HRECOS): `python -m pytest -m live -o addopts= -s backend/tests/test_live_endpoints.py`. Only run when asked; CI runs it daily via `live-endpoints.yml`.
- Local API without Docker: `start-api.ps1` (Windows) uses SQLite (`sqlite+aiosqlite`) and disables alerts.
- Full stack: `docker compose up --build` (TimescaleDB + backend on :8000 + frontend on :8080). `make` targets wrap these.
- Lint (matches CI): `cd backend && flake8 app --count --select=E9,F63,F7,F82 --show-source --statistics`. Black and isort run in CI but are non-blocking; don't mass-reformat files you aren't otherwise changing.

### Edge hydrophone node

```bash
cd edge
pip install -r requirements-dev.txt     # FLAC needs libsndfile1
pytest -q
python -m hydrophone_node --config config/poughkeepsie.yaml --dry-run --replay-speed 0 --max-segments 1
```

### Edge sonar node

```bash
cd edge/sonar
pip install -r requirements-dev.txt
pytest -q
python -m sonar_node --config config/westpoint-cornwall.yaml --dry-run --max-tracks 30
```

### ML

```bash
cd ml && pip install -r requirements.txt pytest && pytest -q
cd ml/sonar && pip install -r requirements.txt pytest && pytest -q   # pytest.ini adds ../../edge/sonar/src to the path
```

Contract tests must not download Perch or external corpora. Keep it that way.

### Mobile

```bash
cd mobile
npm install --legacy-peer-deps
npx expo start
```

CI (`build.yml`) runs `npx expo prebuild --platform android` then `./gradlew assembleRelease` on Node 20 / Java 17. `mobile/android/` is generated; don't commit it. API base URL is in `mobile/src/config/api.js` and can be overridden at runtime in Settings (AsyncStorage).

### Supabase

```bash
supabase start && supabase db reset     # local only
```

**Never** run `supabase db reset --remote`. It drops the hosted database. Pushing to a hosted project (`supabase db push --remote`) is a deploy action — ask first.

## CI that must stay green

`.github/workflows/ci.yml` runs on pushes to `main`/`develop` and PRs to `main`:

- `lint-and-test` — backend flake8 (blocking subset), black/isort/bandit (non-blocking)
- `edge-tests` — `pytest -q` in `edge/`
- `edge-image` — builds `edge/Dockerfile` and runs one simulated minute
- `docker-build-test` — builds backend image from **repo root context** and curls `/health`; builds frontend image

Other workflows: `pages.yml` (deploys static site on push to `main`), `build.yml` (APK on mobile changes pushed to `main` or `codex`, or a manual run), `deploy.yml` (SSH deploy on `v*` tags), `security-scan.yml`, `live-endpoints.yml` (daily). Don't add triggers that deploy or publish without being asked.

## Rules that are easy to break

### Station registry

- `data/stations.json` is the only place station ids, coordinates, river miles, and provider URLs are defined. Backend (`backend/app/registry.py`), sonar importer, and Pages all read it.
- `mobile/src/data/stations.json` is a byte-for-byte copy. If you change one, copy it to the other in the same commit.
- The backend image copies it to `/app/data/stations.json`; the backend Dockerfile build context is the repo root for that reason. Don't change the context.
- River miles are NYS DEC miles from The Battery = 0.
- HRECOS left USGS NWIS in 2026. Current values come from the NYS Mesonet CSV API (`nysm.hrecos.org`), not `waterservices.usgs.gov`.
- NOAA **8518490 is New Rochelle**, not Newburgh. Some older docs (e.g. `mobile/README.md`) still say Newburgh. Don't reintroduce it as the Newburgh tide station.

### Data contracts (Supabase / edge / ML / web / mobile)

- Table, column, id, and label names are fixed by `supabase/migrations/`, `contracts/*.schema.json`, and `docs/fish-network.md` / `docs/sonar-track.md`. Changing one means changing all of them together: migration, JSON Schema, writers in `edge/` and `ml/`, readers in `fish-sounds.js` and the mobile app, and the docs.
- New migrations go in `supabase/migrations/` as `YYYYMMDDHHMMSS_description.sql`. Never edit a migration that has already been merged; add a new one.
- Detection labels, in priority order: `bass_spawning_splash`, `sturgeon_thunder`, `drum_knock`, `toadfish_boatwhistle`, `boat`, `unknown`. Don't add, rename, or reorder without updating every place above.
- `species.id` is a text slug (`atlantic_sturgeon`, `striped_bass`, `freshwater_drum`, `oyster_toadfish`, …). `striped_bass` stays `soniferous = false` — the splash is not a vocalization. River herring has no call label.
- Seeded node ids: `westpoint-cornwall`, `poughkeepsie`, `tappan-zee`.
- `detection_counts_hourly.detections` is **calling activity per hour**, not a fish count. `fish_passage_hourly.fish_count` counts sonar tracks. Don't label either as "number of fish" in UI or docs, and don't sum `splash_detections` across sonar directions in `striped_bass_passage_and_calls_hourly`.
- Lowrance imports write `source = lowrance_log`, `direction = unknown`, `species_id = null`. A 30–120 cm mark is `features.bass_candidate`, not a species assignment.
- `storage_path` / `clip_path` are object keys in the `audio` (or `sonar`) bucket, not full URLs.

### Secrets and keys

- The Supabase **anon** key may be committed in `config.js`; RLS makes it read-only. The **service-role** key bypasses RLS and must never appear in `config.js`, `app.js`, `fish-sounds.js`, the mobile app, or any committed file. Edge nodes read it from `SUPABASE_SERVICE_ROLE_KEY` or `/etc/hydrophone/node.env`.
- `.env` is gitignored; `.env.example` holds placeholders only. Don't put real SMTP, Twilio, Slack, Google Maps, SSH, or deploy credentials in any tracked file.
- Leaving `config.js` values empty makes the Sounds tab fall back to `data/fish-sounds.json`. Keep that fallback working.

### ML artifacts and claims

- Metric files (`ml/artifacts/**/metrics*.json`, `ml/sonar/artifacts/synthetic_metrics.json`) are written by scripts. Never hand-edit them. Re-run the script instead.
- Numbers in `ml/README.md` and `ml/sonar/README.md` must come from those files. Don't type in or round metrics by hand.
- Synthetic results are not field results. Don't describe them as accuracy on the river.
- FishSounds data is CC BY-NC 4.0. Don't commit weights trained on it, or the raw audio. `ml/data/**` and `ml/artifacts/cache/` stay local.
- Bump `model_version` when a probe's behavior changes, and put new artifacts under a new version directory rather than overwriting an old one.

### Static site

- GitHub Pages serves the **root** `index.html`, `app.js`, `style.css`, `config.js`, `fish-sounds.js`, `manifest.json`, and `data/fish-sounds.json` — exactly the list in `pages.yml`. A new file the site needs must be added to that copy step, or it won't deploy.
- `frontend/` is the Docker/nginx dashboard and is separate. Changing one does not change the other.
- Maps use Leaflet + OpenStreetMap with no API key. Don't add a keyed map provider to the Pages site.

### Leave alone unless asked

- `*.bak` and `frontend/index.html.cornwall` — old copies, not live code.
- `docker-compose.prod.yml`, `Caddyfile`, `nginx.conf`, `oracle-cloud-*.sh`, `ORACLE-CLOUD-DEPLOY.md`, `.github/workflows/deploy.yml` — production deployment.
- `.github/CODEOWNERS`.

## Working style

- Branch from `main`; open a PR into `main`. Merged PRs are squashed with titles like "Add a sonar passage track for Hudson fish counts (#22)": short, plain, imperative, describing the user-visible change.
- Fill in `.github/pull_request_template.md`. Say which subprojects you touched and which test commands you ran.
- Run the tests for every subproject you change before saying it works. If a change crosses a contract (migration, schema, label), run tests for every writer and reader of it.
- Prefer the smallest change that fixes the problem. Don't restructure directories or reformat unrelated files.
- Write docs and comments in plain, literal sentences — say what a field is and what it is not — matching the existing READMEs.
- If you can't verify something (no network, no Supabase project, no device), say so instead of guessing.
