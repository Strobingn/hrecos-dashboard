# Hudson River fish acoustic network

Shared Postgres contract for hydrophones, sound-event detections, and species. The edge node writes with the service role. The web tab and Android screen read with the anon key. Keep the table, column, and id names in this document.

`detection_counts_hourly.detections` is **calling activity per hour**: how many non-rejected sound events were detected in that UTC hour. It is not a count of individual fish. One fish can call many times, and many fish can be silent. Boat and unknown labels are events too.

## Tables

All objects are in schema `public`.

| Name | What a row is |
| --- | --- |
| `species` | A fish. `id` is a text slug (`atlantic_sturgeon`). `soniferous` is false for reference species, including shortnose sturgeon, whose sound production is unconfirmed. |
| `hydrophone_nodes` | A hydrophone. `status` is `online`, `offline`, or `simulated`. |
| `audio_segments` | Metadata for one stored clip. `storage_path` is an object key in the Storage bucket `audio`, not a full URL. |
| `detections` | One detected sound. `label` examples: `sturgeon_thunder`, `drum_knock`, `toadfish_boatwhistle`, `boat`, `unknown`. `confidence` is 0–1. `review_status` is `unreviewed`, `confirmed`, or `rejected`. `clip_path` is an object key in bucket `audio`, or null. |
| `detection_counts_hourly` | View. Columns: `node_id`, `species_id`, `label`, `hour`, `detections`, `avg_confidence`. `hour` is the UTC start of the hour (`date_trunc` on `start_time`). Rejected rows are excluded. `species_id` can be null. |

JSON Schemas for those five shapes live in `contracts/`. Writers may omit database defaults (`id` on uuid tables, `created_at`, `review_status`, node `status`).

Seeded node ids:

- `westpoint-cornwall` — West Point / Cornwall, about river mile 54
- `poughkeepsie` — Poughkeepsie, river mile 75
- `tappan-zee` — Tappan Zee / Piermont, river mile 26

All three are `status = simulated`.

## Access

Row Level Security is on. `anon` and `authenticated` can `select` species, hydrophone nodes, audio-segment metadata, detections, and the hourly view. They cannot insert, update, or delete. Writes use `service_role`, which bypasses RLS. Do not put the service role key in the web or Android client.

Realtime is enabled on `detections` and `hydrophone_nodes` (they are members of the `supabase_realtime` publication, with `replica identity full`).

Storage bucket `audio` is public-read, including the anonymous object URL:

`{SUPABASE_URL}/storage/v1/object/public/audio/{storage_path}`

Uploads are service-role only. The bucket allows common audio types and `application/octet-stream`, up to 100 MiB.

## Apply with the Supabase CLI

No hosted project is required to merge this schema. Docker is required for a local stack. Commands below match Supabase CLI 3 (`supabase db push` is local unless you pass `--remote`).

```bash
# Local stack: migrations, then supabase/seed.sql
supabase start
supabase db reset

# Hosted project, after `supabase login`
supabase link --project-ref <project-ref>
supabase db push --remote --include-seed
```

`--include-seed` loads `supabase/seed.sql` (configured in `supabase/config.toml` under `[db.seed]`). To apply the seed on its own:

```bash
supabase db query --remote -f supabase/seed.sql
```

Do not run `supabase db reset --remote` against a project that already has data. Reset drops the database.

On a plain Postgres server the migration still creates the tables, view, indexes, and RLS. It skips the `audio` bucket and Realtime publication when the Supabase `storage` schema and `supabase_realtime` publication are absent, and raises if the `auth` schema is present but those pieces are missing.

Sonar passage counts (individual tracks, not calling activity) are a separate contract: `sonar_nodes`, `sonar_tracks`, `fish_passage_hourly`, and `striped_bass_passage_and_calls_hourly`. See `docs/sonar-track.md`. The striped bass fusion view expects hydrophone rows with `label = bass_spawning_splash` and `species_id = striped_bass` when a spawning splash is detected. Those detection totals are hour-level and must not be summed across sonar directions.
