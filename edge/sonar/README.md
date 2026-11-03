# Sonar node

Synthetic imaging-sonar node for the Hudson. It writes the same rows a fixed ARIS or split-beam counter would write: one track per fish that passed through the beam. No sonar is attached. The generator and the length rules are described in `docs/sonar-track.md`.

Seeded site: `westpoint-cornwall`. `poughkeepsie` and `tappan-zee` are later sites. Their config files exist, and an upload would upsert the node, but the migration does not seed them.

## What gets written

- `sonar_nodes` — upserted on the heartbeat
- `sonar_tracks` — one row per track. `direction` is `upstream`, `downstream`, or `milling`. `species_id` is the classifier guess or null. `review_status` is `unreviewed`. `clip_path` is an object key in the Storage bucket `sonar`
- The clip is a JSON sidecar with `"synthetic": true`. It is not an ARIS frame. The hidden truth species is not in the clip and is not uploaded. A dry run writes it to `truth.jsonl` so an evaluation can score the guess.

`fish_passage_hourly.fish_count` counts these tracks. It is not `detection_counts_hourly`. Synthetic rows set `source` to `synthetic`.

## Lowrance `.sl2` / `.sl3` import

Dirk's unit is Primary and Secondary CHIRP, DownScan, and SideScan. It has no ActiveTarget. A log from an anchored boat is an index of fish that passed under the boat, not a river count. Species is left null. A 30–120 cm mark is `features.bass_candidate`, not `species_id = striped_bass`. How to record the file is in `docs/sonar-track.md`.

```bash
cd edge/sonar
pip install -e .
python -m sonar.import_lowrance file.sl2 --node westpoint-cornwall --dry-run
```

`PYTHONPATH=src` works instead of the editable install. `--dry-run` writes `out/sonar_tracks.jsonl` and does not use the network. Omit `--node` only when the GPS fix is on the Hudson: the nearest row in `data/stations.json` is mapped to a sonar site (`west_point` → `westpoint-cornwall`). `direction` is `unknown`. `source` is `lowrance_log`. Unclassified rows do not appear in `fish_passage_hourly`.

During the striped bass spawn the generator builds surface clusters: several fish, depth under about 1.5 m, mostly `milling`. That is the rock-fight behavior. The hydrophone label for the splash is `bass_spawning_splash`. This process does not write that detection. The view `striped_bass_passage_and_calls_hourly` joins the two after both exist. Do not sum `splash_detections` across directions.

## Run a dry pass

```bash
cd edge/sonar
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m sonar_node \
  --config config/westpoint-cornwall.yaml \
  --dry-run \
  --max-tracks 30
```

Stdout is logs. JSONL is under `out/`.

## Classifier

`classifier.name: rules` is `length_behavior_rules` version `0.1.0`. It uses observed length, depth, and the behavior summary. It does not read images.

A later model, including one that classifies ARIS frames, plugs in without changing the publisher:

```yaml
classifier:
  name: ml
  entrypoint: hrecos_sonar.plugin:build_classifier
```

`build_classifier` returns an object with `classify(track) -> Classification`. `classify_frames` on the rules baseline raises `NotImplementedError`. Frame stacks, when a real model exists, are float arrays shaped `(n_frames, height, width)`.

## Environment

| Variable | Overrides |
| --- | --- |
| `NODE_ID` | `node.id` |
| `SONAR_SOURCE` | `source.kind` (only `synth`) |
| `SONAR_RATE` | `source.rate` |
| `REPLAY_SPEED` | accepted and ignored; tracks are written as a batch |
| `SUPABASE_URL` | `supabase.url` |
| `SUPABASE_SERVICE_ROLE_KEY` | `supabase.service_role_key` |

```bash
export SUPABASE_URL=https://YOUR_PROJECT.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
python -m sonar_node --config config/westpoint-cornwall.yaml --max-tracks 30
```
