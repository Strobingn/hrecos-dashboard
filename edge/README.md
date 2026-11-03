# Hydrophone node

Virtual Hudson River hydrophone node. It runs the same path a Raspberry Pi will run with an [Aquarian H2a](https://www.aquarianaudio.com/h2a-hydrophone.html): read a continuous stream, cut 60-second segments, measure levels, detect calls, upload metadata and short clips.

Today the stream is a folder of WAV/FLAC files, the public NOAA NCEI bucket `gs://noaa-passive-bioacoustic/`, or a synthesizer. On the Pi, set `source.kind: device` and the same process reads the USB audio interface the H2a is plugged into.

Simulated node ids (coordinates are filled in when you omit them):

| id | place | river mile |
| --- | --- | --- |
| `westpoint-cornwall` | West Point channel | 52.5 |
| `poughkeepsie` | Poughkeepsie waterfront | 75.6 |
| `tappan-zee` | Tappan Zee | 27.4 |

River miles are counted from The Battery. `status` for this process is `simulated`. A Pi reporting real audio should set `status: online`.

## What gets written

Supabase tables (the migrations are owned separately; these names match them):

- `hydrophone_nodes` — one row per node, upserted on every heartbeat
- `audio_segments` — one row per 60 s segment. `band_levels` is jsonb with keys `10-100`, `100-500`, `500-2000`. `storage_path` is an object in the Storage bucket `audio`
- `detections` — `label` is `sturgeon_thunder`, `drum_knock`, `toadfish_boatwhistle`, `boat`, or `unknown`. `species_id` is `atlantic_sturgeon`, `freshwater_drum`, `oyster_toadfish`, or null. `review_status` is `unreviewed`

`rms_db` and the band levels are `20*log10(RMS)` of the float samples, plus `calibration_offset_db`. Offset `0` means dBFS (full scale is 0 dB). Add the H2a sensitivity and preamp gain on the Pi when you want dB re 1 µPa.

The service role key is read from `SUPABASE_SERVICE_ROLE_KEY`. It bypasses RLS. Keep it in the environment or in `/etc/hydrophone/node.env`, not in git.

## Run a dry pass

No Supabase project is required. Stdout is JSON lines (heartbeat, then each segment, then each detection). The same objects are written under `out/`.

```bash
cd edge
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m hydrophone_node \
  --config config/poughkeepsie.yaml \
  --dry-run \
  --replay-speed 0 \
  --max-segments 1
```

`--replay-speed 1` sleeps so one minute of audio takes one minute of wall clock. `10` is ten times faster. `0` does not sleep. Live `device` input ignores replay speed because the sound card is already real-time.

Other nodes: `config/westpoint-cornwall.yaml`, `config/tappan-zee.yaml`. `config.example.yaml` lists every field.

## Audio sources

`source.kind` in the YAML, or `HYDROPHONE_SOURCE`.

**synth** (the default in the sample configs). Continuous background: broadband noise, distant boat rumble, and 60 Hz hum, with one of each call per segment:

- Atlantic sturgeon spawning thunder: about 1.9 s of percussive beats, energy in 10–100 Hz, peak near 44 Hz
- Freshwater drum: about 25 knocks near 400 Hz across about 0.8 s
- Oyster toadfish boatwhistle: a short harmonic tone near 200 Hz
- a closer boat pass later in the segment

`source.calls: false` leaves the noise bed with no injected calls. `source.duration_s` stops the synthesizer; leave it empty to run until the process is stopped. `source.seed` fixes the noise.

**folder.** Every `.wav` and `.flac` under `source.path` (or `HYDROPHONE_SOURCE_PATH`), sorted by path, as one stream. Files are resampled to `sample_rate_hz`. WAV is read with the standard library; FLAC needs `libsndfile` (installed in the Docker image).

```yaml
source:
  kind: folder
  path: /data/hudson-wavs
  max_files: 100
```

**noaa.** Anonymous HTTPS against the public NOAA NCEI passive acoustic archive. No Google credentials.

```yaml
source:
  kind: noaa
  bucket: noaa-passive-bioacoustic
  prefix: sanctsound/
  max_files: 3
```

`prefix` is required in practice. The bucket holds many projects (`sanctsound/`, `nrs/`, `adeon/`, and others) and listing a wide prefix downloads a lot of audio. Objects are fetched from `https://storage.googleapis.com/noaa-passive-bioacoustic/<object>`.

**device.** The Pi path. `source.device` is a [sounddevice](https://python-sounddevice.readthedocs.io/) name such as `hw:1,0`. Install the extra with `pip install sounddevice` (the `pi` extra in `pyproject.toml`). The H2a is analog; the Pi digitizes it with a USB audio interface at `sample_rate_hz` (48 kHz in the sample configs).

## Detector

`detector.name: band_energy` is the baseline (`model_name=band_energy`, `model_version=1.0.0`). It is a small rule set on band energy, pulse rate, and tonal peaks, written so it fires on the synthetic templates above.

Replace it with a model without touching the pipeline:

```yaml
detector:
  name: ml
  entrypoint: my_package.plugin:build_detector
```

`build_detector` must return an object with `detect(samples, sample_rate, segment_start) -> list[DetectionEvent]`. Copy the fields from `hydrophone_node.detect.base.DetectionEvent`. Labels and species ids have to stay inside the contract or the row is rejected before upload.

## Environment

| Variable | Overrides |
| --- | --- |
| `NODE_ID` | `node.id` |
| `SAMPLE_RATE_HZ` | `node.sample_rate_hz` |
| `HYDROPHONE_SOURCE` | `source.kind` |
| `HYDROPHONE_SOURCE_PATH` | `source.path` (used as the NOAA prefix when `NOAA_PREFIX` is unset) |
| `NOAA_PREFIX` | `source.prefix` |
| `REPLAY_SPEED` | `replay_speed` |
| `SUPABASE_URL` | `supabase.url` |
| `SUPABASE_SERVICE_ROLE_KEY` | `supabase.service_role_key` |

`${SUPABASE_URL}` inside the YAML is expanded from the environment. A real upload:

```bash
export SUPABASE_URL=https://YOUR_PROJECT.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
python -m hydrophone_node --config config/poughkeepsie.yaml --replay-speed 0 --max-segments 1
```

Heartbeats upsert `hydrophone_nodes`. Segment audio and clips go to the `audio` bucket at `storage_path` and `clip_path`. A `SIGTERM` (the systemd stop signal) sends one last heartbeat and exits.

## Docker

```bash
docker build -t hydrophone-node edge
docker run --rm hydrophone-node
```

That default runs one simulated minute for Poughkeepsie and exits. Arguments after the image name replace that default. Mount a node config and pass the service role key to upload:

```bash
docker run --rm \
  -v /etc/hydrophone/node.yaml:/config/node.yaml:ro \
  -e SUPABASE_URL -e SUPABASE_SERVICE_ROLE_KEY \
  hydrophone-node --config /config/node.yaml
```

## Raspberry Pi

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin hydrophone
sudo mkdir -p /opt/hydrophone /etc/hydrophone
sudo rsync -a edge/ /opt/hydrophone/
sudo python3 -m venv /opt/hydrophone/.venv
sudo /opt/hydrophone/.venv/bin/pip install -r /opt/hydrophone/requirements.txt sounddevice
sudo cp edge/deploy/hydrophone-node.service /etc/systemd/system/
```

`/etc/hydrophone/node.yaml` is the Pi config (`source.kind: device`, `status: online`). `/etc/hydrophone/node.env` holds `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

```bash
sudo systemctl enable --now hydrophone-node
journalctl -u hydrophone-node -f
```

Confirm the H2a interface with `arecord -l` and set `source.device` to that card. `sample_rate_hz` has to be a rate the interface actually supports.

## Tests

```bash
cd edge
pip install -r requirements-dev.txt
pytest
```

Detector tests synthesize each call into noise (including boat rumble and 60 Hz hum) and require the matching label. The dry-run test checks the JSON keys against the table contract and fails if anything opens a socket.

## Layout

```
edge/
  config/                      sample node YAML
  deploy/hydrophone-node.service
  src/hydrophone_node/
    audio/                     sources, 60 s segmenter, levels, synthesizer
    detect/                    Detector interface and band-energy baseline
    publish/                   dry-run JSON and supabase-py uploader
    pipeline.py                heartbeat, segment, detect, upload
    cli.py
  tests/
  Dockerfile
```
