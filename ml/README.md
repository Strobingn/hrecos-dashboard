# Hudson River fish-sound baseline

Offline classifier for hydrophone audio, meant to stand in for a rule-based detector on an edge node. It freezes Google's **Perch 2.0** embedding model and trains a logistic-regression probe on top. The run below is CPU-only (ONNX Runtime). No metric in this file was typed in by hand; they are the numbers in [`artifacts/hrecos-fish-probe/0.2.0/metrics.json`](artifacts/hrecos-fish-probe/0.2.0/metrics.json) from the run on 2026-11-03.

`model_name` is `hrecos-fish-probe` and `model_version` is `0.2.0`. Detection labels are `sturgeon_thunder`, `drum_knock`, `toadfish_boatwhistle`, `bass_spawning_splash`, `boat`, and `unknown`. Rows go into `public.detections`. `to_detection_rows` validates against `contracts/detections.schema.json`.

## Result in one paragraph

On a held-out synthetic test set (24 clips per class, 240 clips, ten classes), the deployed Perch probe has accuracy **0.9917** (238/240) and macro-F1 **0.9917**. That score is the synthesizer recognizing itself. The same head, on real audio it was not trained on, does worse than `0.1.0`. Both Atlantic sturgeon supplementary clips are now `hum_60hz` on the center 5 s window (confidence 0.994 and 0.998), and `detect()` writes them as `unknown` (AS1 0.00–7.00 s, confidence 0.998, band 28.4–56.6 Hz; AS2 0.00–6.00 s, confidence 0.998). `0.1.0` had called both center windows `sturgeon_thunder`. Three of four freshwater-drum calls are also `hum_60hz` at the center window; only drum call 3 still produces a `drum_knock` under the sliding window (1.00–2.45 s, confidence 0.573), overlapping an `unknown`. Both toadfish proxies remain `toadfish_boatwhistle`. The two unlabeled Hudson excerpts are `unknown` (the 60 Hz class) and `boat`.

Long synthetic sequences, which are the check Dirk asked for, separate cleanly at 5 s already, so the temporal gate does not move them. Of 8 stop-start wakes (90 s each), **0/8** emit `bass_spawning_splash` with the gate off and **0/8** with it on; **8/8** emit `boat` either way. Of 8 splash bouts, **8/8** still emit `bass_spawning_splash` with the gate on, and **6/8** also emit `boat` somewhere in the file with the gate off and on. The gate is exercised by a unit test that plants a splash label on a wake and checks that it becomes `boat`. There is no real striped-bass splash recording in this run.

A fixed low-frequency descriptor scores **0.9958** on the synthetic test and then calls both real sturgeon clips `bass_spawning_splash`. Concatenating it with Perch also scores **0.9958** and still misses both sturgeon clips (`hum_60hz`). Mean absolute coefficient after standardization is 0.0098 on the 1536 Perch features and 0.0294 on the 26 low-band features. The deployed artifact stays the Perch probe alone. Those 11 real files were already inspected when `0.1.0` chose Perch over the low-band head, so they are not a locked test set. Adding `bass_spawning_splash`, `rain`, and `wave_slap` moved the boundary; this file reports that move and does not retune to get the sturgeon clips back.

## Why Perch 2.0, and not SurfPerch, for this run

SurfPerch (Zenodo [11060189](https://zenodo.org/records/11060189), Williams et al. 2024) is the closer pretraining domain: underwater sound, 32 kHz, 5 s windows, **1280-d** embeddings. The published bundle is a TensorFlow SavedModel. Perch 2.0 is a later Google bioacoustics model (EfficientNet-B3, trained on Xeno-canto, iNaturalist, Animal Sound Archive, and FSD50K, including non-avian taxa). Its backbone consumes the same 5 s / 32 kHz contract and returns a **1536-d** embedding. A numerically checked ONNX export of the backbone is about 45 MB and ran here at roughly 30–40 ms per window on CPU.

`hrecos_ml.embeddings.SurfPerchTFEmbedder` will load a SurfPerch SavedModel if TensorFlow is installed. It was not executed in this run. `scripts/download_data.py --surfperch` fetches the 128 MB Zenodo zip and does not unpack it into git.

## Labels

Training classes are the four fish-related sounds plus `boat`, `train`, `hum_60hz`, `rain`, `wave_slap`, and `background`. At inference, `train`, `hum_60hz`, `rain`, and `wave_slap` are written as `unknown`. Plain `background` is not written at all. A window is kept when its winning class is in that emitted set and its probability is at least 0.5.

`bass_spawning_splash` is a surface splash from a striped bass spawning rock fight (several males bumping a female at the surface), not a vocalization. `species.soniferous` for `striped_bass` stays false. No peer-reviewed spectrum of that splash was found. The synthetic hits follow generic splash physics: a short broadband impact plus a damped bubble (Franz 1959, JASA 31:1080). Spawning at or near the surface, often near 15–20 °C within a wider 10–23 °C range, is in Setzler et al. 1980, NOAA Technical Report NMFS Circular 433. Hudson egg distributions in Secor et al. 2020 (PLOS ONE 15(11):e0242797) put spawning reaches upriver of Kingston and through the West Point–Poughkeepsie stretch. Evening and night are when several rivers concentrate the behavior; that clock time is not an audio feature and is not a field on the detection row.

Boat wake, in the field note this version encodes, is constant or stop-start over tens of seconds to minutes, often with engine rumble before the wash. Spawning splashes are short impulsive bursts in clusters. Because the probe only sees 5 s, `detect()` runs `hrecos_ml.temporal.gate_splash_labels` on buffers of at least 30 s. Over about 90 s of envelope it measures burst duration, duty cycle, and the gaps between bursts. A splash label that sits on an elevated block of at least 8 s, or anywhere between two such blocks, is rewritten to `boat` with `species_id` null. Buffers shorter than 30 s are not gated.

Rain is a stationary field of small-drop impacts with a type-I bubble tone near 15 kHz (Nystuen 1986, JASA 79:972; Medwin, Nystuen, Jacobus, Ostwald, and Snyder 1992, JASA 92:1613). Wave slap is a quasi-periodic low-frequency thump. Both are training negatives and collapse to `unknown`.

| Detection label | `species_id` | Organism | What the synthesizer used |
| --- | --- | --- | --- |
| `sturgeon_thunder` | `atlantic_sturgeon` | *Acipenser oxyrinchus* | 10–100 Hz, peak near 44 Hz, bout about 1.9 s (Cohen et al. 2025, [doi:10.3354/esr01429](https://doi.org/10.3354/esr01429)) |
| `drum_knock` | `freshwater_drum` | *Aplodinotus grunniens* | knock train centered near 400 Hz |
| `toadfish_boatwhistle` | `oyster_toadfish` | *Opsanus tau* | tonal boatwhistle, fundamental roughly 110–240 Hz plus harmonics |
| `bass_spawning_splash` | `striped_bass` | *Morone saxatilis* | broadband hits of 40–280 ms, a few per 5 s window; no measured bass spectrum |
| `boat` | null | vessel | engine line that is not 60 Hz, or a 5 s crop of a long stop-start wake |
| `unknown` | null | train, 60 Hz hum, rain, wave slap, or other non-target | |

`species_id` is the primary key of `public.species` in `supabase/seed.sql`.

`freq_low_hz` and `freq_high_hz` on a detection are the 10th and 90th percentiles of spectral energy from 10 to 4000 Hz on the winning window. They are measured from the audio. The bands above are not copied into those fields.

## What was trained

The committed weights (`0.2.0`) were fit only on synthetic clips from `hrecos_ml.synthesize`. FishSounds is CC BY-NC 4.0, so a probe trained on those files is not in the git tree. Real recordings are an external check, plus a leave-one-file-out probe that is fit in memory and discarded. `0.1.0` is no longer the artifact `detect()` loads.

Each synthetic clip is 5 s at 32 kHz. The target is mixed with pink noise at a random SNR from −2 to 16 dB, a weak 60 Hz line is added to every class (only `hum_60hz` is dominated by it), and about a third of the sturgeon, drum, and toadfish clips also carry a quieter boat. Splash clips do not. Half of the `boat` clips are crops of a 70 s stop-start wake. Train split: 48 clips per class, seed `20260311` (480 clips). Test split: 24 per class, seed `20260917` (240 clips). The probe is `StandardScaler` plus L2 logistic regression (`C=1`, `class_weight="balanced"`).

Package versions for that fit: Python 3.12.3, numpy 2.5.4, scipy 1.18.1, scikit-learn 1.9.1, onnxruntime 1.31.1, onnx 1.23.2.

## Synthetic test (deployed Perch probe)

Rows of the confusion matrix are the true class, columns the predicted class, in this order: sturgeon, drum, toadfish, bass splash, boat, train, hum, rain, wave slap, background.

|  | sturgeon | drum | toadfish | bass | boat | train | hum | rain | wave | background |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sturgeon | 24 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drum | 0 | 24 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| toadfish | 0 | 0 | 24 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| bass | 0 | 0 | 0 | 24 | 0 | 0 | 0 | 0 | 0 | 0 |
| boat | 0 | 0 | 0 | 0 | 23 | 0 | 1 | 0 | 0 | 0 |
| train | 0 | 0 | 0 | 0 | 0 | 24 | 0 | 0 | 0 | 0 |
| hum | 0 | 0 | 0 | 0 | 1 | 0 | 23 | 0 | 0 | 0 |
| rain | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 | 0 | 0 |
| wave | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 | 0 |
| background | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| sturgeon_thunder | 1.0000 | 1.0000 | 1.0000 | 24 |
| drum_knock | 1.0000 | 1.0000 | 1.0000 | 24 |
| toadfish_boatwhistle | 1.0000 | 1.0000 | 1.0000 | 24 |
| bass_spawning_splash | 1.0000 | 1.0000 | 1.0000 | 24 |
| boat | 0.9583 | 0.9583 | 0.9583 | 24 |
| train | 1.0000 | 1.0000 | 1.0000 | 24 |
| hum_60hz | 0.9583 | 0.9583 | 0.9583 | 24 |
| rain | 1.0000 | 1.0000 | 1.0000 | 24 |
| wave_slap | 1.0000 | 1.0000 | 1.0000 | 24 |
| background | 1.0000 | 1.0000 | 1.0000 | 24 |

The other two heads, same split:

| Head | Features | Accuracy | Macro-F1 |
| --- | ---: | ---: | ---: |
| Perch 2.0 (deployed) | 1536 | 0.9917 | 0.9917 |
| low-band descriptor | 26 | 0.9958 | 0.9958 |
| Perch + low-band | 1562 | 0.9958 | 0.9958 |

Sliding-window check on synthetic scenes (a 5 s clip mixed into 15 s of synthetic background at a known offset; 8 scenes per class). These buffers are shorter than 30 s, so the splash gate does not run. A hit is a detection of the mapped label overlapping that 5 s span.

| Class | Detection label | Hits | Median absolute start error (s) |
| --- | --- | ---: | ---: |
| sturgeon_thunder | sturgeon_thunder | 7/8 | 2.35 |
| drum_knock | drum_knock | 8/8 | 3.51 |
| toadfish_boatwhistle | toadfish_boatwhistle | 8/8 | 1.77 |
| bass_spawning_splash | bass_spawning_splash | 8/8 | 3.64 |
| boat | boat | 6/8 | 2.64 |
| train | unknown | 8/8 | 3.14 |
| hum_60hz | unknown | 8/8 | 2.31 |
| rain | unknown | 8/8 | 3.49 |
| wave_slap | unknown | 8/8 | 2.54 |

Six synthetic background-only scenes produced a detection in **6/6**. The labels on those scenes were `boat` and `sturgeon_thunder`. The generator is the same family the probe was trained on, so these rates are a pipeline check, and this one says the probe fires on its own noise floor.

### Stop-start wakes and splash bouts

Eight 90 s stop-start wakes (engine, a wash of tens of seconds, a gap, another wash) and eight 90 s splash bouts. A file counts if `detect()` emits the label anywhere. `temporal_gate=False` is the 5 s probe alone.

| Sequence | Splash, gate off | Splash, gate on | Boat, gate off | Boat, gate on |
| --- | ---: | ---: | ---: | ---: |
| stop-start wake | 0/8 | 0/8 | 8/8 | 8/8 |
| splash bout | 8/8 | 8/8 | 6/8 | 6/8 |

The wake family is also what half of the 5 s `boat` training clips are cropped from, so this is not an unseen negative. The gate's job is the case where a 5 s slice of a long wash is still labeled splash. That case did not occur in these 8 files.

## Real recordings

Every download in the earlier run succeeded and was reused. The log is [`artifacts/data_access.json`](artifacts/data_access.json). Audio stays in `ml/data/` and is gitignored. Nothing here is a striped bass splash.

**FishSounds** ([doi:10.5683/SP2/TACOUX](https://doi.org/10.5683/SP2/TACOUX), Borealis, CC BY-NC 4.0). The Dataverse dataset has freshwater drum and toadfish-like boatwhistles. It does not have Atlantic sturgeon or oyster toadfish. Clips used:

- *Aplodinotus grunniens* drum calls, Rountree 2017, file ids 200686, 200719, 200764, 200676
- *Opsanus beta* (gulf toadfish, not *O. tau*) complex call, Looby 2022, file id 843171, labeled `toadfish_boatwhistle` as a proxy
- *Opsanus beta* grunt, file id 843165, left unscored
- *Halobatrachus didactylus* (Lusitanian toadfish) boatwhistle, Amorim 2008, file id 200588, also a proxy

Do not redistribute those wav files. Attribution: Looby, A., Riera, A., Vela, S., Cox, K., Bravo, S., Rountree, R., Juanes, F., Reynolds, L. K., and Martin, C. W. (2021). FishSounds Website Data Repository. https://doi.org/10.5683/SP2/TACOUX, Borealis, V10.

**Sturgeon exemplars.** Supplementary audio of Cohen et al. 2025, Endangered Species Research, [doi:10.3354/esr01429](https://doi.org/10.3354/esr01429): `n058p001_AS1.mp3` (wild thunder) and `n058p001_AS2.mp3` (captive thunder), from `https://www.int-res.com/articles/suppl/`. Not redistributed.

**NOAA NCEI** bucket `gs://noaa-passive-bioacoustic/`. The archive is public. Boat events are not labeled in the object names, and the Hudson files are multi-hundred-MB FLACs, so the long wakes in training stay synthetic. For background, the first 12 MB of two files were fetched and ffmpeg decoded the first 20 s:

- `cornell/audio/noaa_nerrs/as/noaa-nerrs_hudsonriver_2023-2024_as_02/audio/144488Hudson_024K_AS02_ST300-5683_20210424_090503Zm0400.flac`
- `cornell/audio/noaa_nerrs/as/noaa-nerrs_hudsonriver_2023-2024_as_05/audio/144488Hudson_024K_AS05_ST300-5683_20210701_203738Zm0400.flac`

Center-window prediction of the deployed probe (one 5 s window per file, not sliding):

| File | Reference | Prediction | Confidence |
| --- | --- | --- | ---: |
| 200686 drum call 1 | drum_knock | hum_60hz | 0.754 |
| 200719 drum call 2 | drum_knock | hum_60hz | 0.794 |
| 200764 drum call 3 | drum_knock | hum_60hz | 0.511 |
| 200676 drum chorus | drum_knock | hum_60hz | 0.993 |
| 843171 *O. beta* complex call | toadfish_boatwhistle | toadfish_boatwhistle | 0.977 |
| 843165 *O. beta* grunt | unscored | bass_spawning_splash | 0.303 |
| 200588 *H. didactylus* boatwhistle | toadfish_boatwhistle | toadfish_boatwhistle | 0.977 |
| AS1 wild sturgeon | sturgeon_thunder | hum_60hz | 0.994 |
| AS2 captive sturgeon | sturgeon_thunder | hum_60hz | 0.998 |
| Hudson AS02 excerpt | background | hum_60hz | 0.980 |
| Hudson AS05 excerpt | background | boat | 0.983 |

`detect()` on the whole file (the splash gate runs only when the buffer is at least 30 s; the Hudson excerpts are 20 s):

- AS1: `unknown` 0.00–7.00 s, confidence 0.998, band 28.4–56.6 Hz. Not `sturgeon_thunder`.
- AS2: `unknown` 0.00–6.00 s, confidence 0.998, band 24.8–906.2 Hz.
- Drum calls 1 and 2 are `unknown`. Call 3 is `unknown` 0.00–2.45 s (0.511) and `drum_knock` 1.00–2.45 s (0.573, `freshwater_drum`). The chorus is `unknown` across the file (0.995).
- Both toadfish proxies come back as `toadfish_boatwhistle`. The Lusitanian toadfish file is a minute long and also produces `unknown` segments. No `bass_spawning_splash` row.
- The grunt produces no detection (center-window splash probability 0.303, under 0.5).
- Hudson AS02: `unknown` 0.00–20.00 s (0.996). Hudson AS05: `boat` 0.00–20.00 s (0.999).

Leave-one-file-out on the Perch features (synthetic train, plus the other real fish clips, held-out file never seen): **6/8** correct. Misses: drum call 1 predicted `toadfish_boatwhistle` (0.603), and AS1 predicted `background` (0.970). AS2 is `sturgeon_thunder` (0.876) once the other sturgeon clip is in the training fold. That is two sturgeon files, not a validation set.

## Cornell / Hudson River NERR

The recording set to train on next is the annotated Hudson River passive-acoustic collection associated with the NERRS project (Rice and colleagues; NOAA-NERRS Hudson River 2023–2024). The NERRS data description tells users to reach the archive through the [NCEI passive acoustic viewer](https://www.ncei.noaa.gov/maps/passive-acoustic-data/) and `pad.info@noaa.gov`. As of this run the raw 24 kHz FLAC is also listable at `gs://noaa-passive-bioacoustic/cornell/audio/noaa_nerrs/` (deployments `as`, `ich`, `pch`, `sch`, `ss`, `tch`). Filenames are not call labels. `cornell/products/detections/` in that bucket is a Gulf of Mexico sperm-whale table, not Hudson fish marks. A labeled subset is still the right thing to request from Cornell / Hudson River NERR before replacing the edge detector. A real striped-bass splash recording is not in the files above.

## Interface

```python
from datetime import datetime, timezone
from hrecos_ml.infer import detect, to_detection_rows

events = detect(audio, sample_rate)  # samples, hertz
rows = to_detection_rows(
    events,
    node_id="westpoint-cornwall",
    origin=datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc),
)
```

`detect` times are seconds from the start of the buffer. `to_detection_rows` turns them into `public.detections` objects: `start_time` and `end_time` become timezone-aware ISO timestamps, `node_id` is set, and `species_id` stays the seed slug or null. Those objects validate against `contracts/detections.schema.json`.

Each event:

```text
start_time, end_time          seconds from the start of audio
label                         one of the six detection labels
species_id                    species-table slug, or None for boat and unknown
confidence                    probability of the winning training class
freq_low_hz, freq_high_hz     measured energy percentiles
model_name, model_version     hrecos-fish-probe, 0.2.0
```

Audio is resampled to 32 kHz. Windows are 5 s with a 1 s hop. On buffers of at least 30 s, splash labels inside a sustained or stop-start wash are relabeled `boat` before windows merge. Pass `temporal_gate=False` to keep the raw 5 s decisions. The Perch ONNX file is not in git. `detect` looks for `ml/data/models/perch_v2_backbone.onnx`.

## Raspberry Pi

The linear head is exported two ways:

- `artifacts/hrecos-fish-probe/0.2.0/probe.npz`, loaded by NumPy (no pickle)
- `artifacts/hrecos-fish-probe/0.2.0/probe.onnx`, a Gemm plus Softmax (`features` float32 `[batch, 1536]` to `probabilities`)

On a Pi, run the backbone with the TFLite file from the same Hugging Face repo (`biodiversica/Perch-onnx-backbone`, file `perch_v2_backbone.tflite`, about 43 MB) and then either ONNX Runtime or NumPy for the head. `scripts/download_data.py --tflite` fetches that file. This run did not execute TFLite; the backbone that was actually run is the ONNX file under ONNX Runtime.

`scripts/export_model.py` rewrites `probe.onnx` from the npz. A unit test checks that ONNX probabilities match the NumPy probe within 1e-5.

## Reproduce

```bash
cd ml
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/run_baseline.py
python -m pytest tests
```

Individual steps:

| Script | Role |
| --- | --- |
| `scripts/download_data.py` | Perch ONNX, FishSounds wavs, sturgeon mp3s, Hudson excerpts |
| `scripts/synthesize_data.py` | Synthetic train and test wavs |
| `scripts/compute_embeddings.py` | Perch and low-band matrices |
| `scripts/train.py` | Fit probes, write `0.2.0` |
| `scripts/evaluate.py` | Confusion matrix, real files, event timing, wake vs splash sequences |
| `scripts/export_model.py` | Rewrite the ONNX head |

`ml/data/` and `ml/artifacts/cache/` are gitignored. The small probe, metrics, and the download log are not.

## What this does not show

The synthetic classes were built from the same frequency story the low-band features measure, so a high synthetic score is not evidence about the Hudson. Perch's frontend was designed for birds. `0.2.0` loses both sturgeon center windows that `0.1.0` had, and it labels most of the drum calls as hum. The long-wake check never asked the temporal gate to correct a splash, because the 5 s probe already said `boat`. Six of eight splash bouts also contain a `boat` label that the gate does not remove. Annotated river audio, including an actual rock-fight splash, is the next training set.
