# Hudson River fish-sound baseline

Offline classifier for hydrophone audio, meant to stand in for a rule-based detector on an edge node. It freezes Google's **Perch 2.0** embedding model and trains a logistic-regression probe on top. The run below is CPU-only (ONNX Runtime). No metric in this file was typed in by hand; they are the numbers in [`artifacts/hrecos-fish-probe/0.2.1/metrics.json`](artifacts/hrecos-fish-probe/0.2.1/metrics.json) from the run on 2026-11-03.

`model_name` is `hrecos-fish-probe` and `model_version` is `0.2.1`. The species priority is striped bass, then Atlantic sturgeon, then river herring. Herring has no call label (`soniferous` stays false). Detection labels, in that priority order, are `bass_spawning_splash`, `sturgeon_thunder`, `drum_knock`, `toadfish_boatwhistle`, `boat`, and `unknown`. Rows go into `public.detections`. `to_detection_rows` validates against `contracts/detections.schema.json`.

## Result in one paragraph

Striped bass is the class this version is built around. On the held-out synthetic test (24 clips per class, 216 clips, nine classes) `bass_spawning_splash` has precision **1.0000** and recall **1.0000**. Eight 90 s splash bouts all emit `bass_spawning_splash` (8/8) and none emit `boat` (0/8), with the temporal gate on or off. Eight 90 s stop-start wakes emit `boat` (8/8) and never `bass_spawning_splash` (0/8). There is still no real striped-bass splash recording, so this is the synthesizer and the gate, not a field score.

Atlantic sturgeon is next, and `0.2.1` puts both real supplements back on `sturgeon_thunder`. Center window: wild AS1 **0.950**, captive AS2 **0.994**. `detect()` keeps both: AS1 0.00–7.00 s, confidence 0.974, band 25.6–91.4 Hz, `species_id` `atlantic_sturgeon`; AS2 0.00–6.00 s, confidence 0.986. `0.2.0` had called both center windows `hum_60hz` (0.994 and 0.998) and `detect()` wrote `unknown` or `boat`. `0.1.0` had the center windows right and kept the wild clip, but `detect()` called the captive clip `boat`. Drum calls 2 and 3 are `drum_knock`. Drum call 1 is still `toadfish_boatwhistle` (0.581), which is what `0.1.0` did. The drum chorus center window is `sturgeon_thunder` at 0.957, and `detect()` emits nothing: almost none of its power is in 10–100 Hz, so the thunder check drops it.

The whole synthetic test, same split, is accuracy **0.9954** (215/216) and macro-F1 **0.9954**. The one error is a sturgeon clip called `boat`. That score is still the synthesizer recognizing itself.

## Why `0.2.0` called real thunder hum

The learned `hum_60hz` class was five harmonics of 60 Hz, decaying across the same 10–100 Hz band as sturgeon thunder (impulsive beats of about 1.9 s, most energy 10–100 Hz, peak near 44 Hz). Real thunder is not a narrow line: on AS1, about 1.5% of the power sits within 1.5 Hz of 60 Hz, and the 10–100 Hz envelope crests. The probe still preferred that hum class at 0.99. Wake crops mixed under the fish clips made it worse: with hum removed but the wash left in the sturgeon examples, the center windows went to rain and boat.

`0.2.1` does two things about that, and leaves the bass clips alone.

- Fish clips (sturgeon, drum, toadfish) get a quiet engine under them, not a slice of wake. Bass clips were never mixed with that wash.
- Hum is not a trained class. `hrecos_ml.hum.steady_mains_hum` labels a window `unknown` only when a steady line at 60, 120, and 180 Hz holds at least 45% of the power from 40 to 400 Hz and the low-band envelope does not crest. A probe label of `sturgeon_thunder` is kept only when at least 40% of the power from 10 Hz up sits in 10–100 Hz and that envelope crests (impulsive beats, not a chorus or a wash).

Those checks were looked at on the same 11 real files used for the `0.1.0` embedder choice. They are not a locked test. Bass synthetic precision stayed 1.0000 while the thunder clips moved back.

A low-band descriptor scores **0.9954** on the synthetic test and then calls both real sturgeon clips `bass_spawning_splash` (0.991 and 0.999). That would spend the bass label on thunder. Concatenating it with Perch scores **1.0000** on the synthetic test. Mean absolute coefficient after standardization is 0.0086 on the 1536 Perch features and 0.0221 on the 26 low-band features. The deployed artifact stays the Perch probe alone.

## Why Perch 2.0, and not SurfPerch, for this run

SurfPerch (Zenodo [11060189](https://zenodo.org/records/11060189), Williams et al. 2024) is the closer pretraining domain: underwater sound, 32 kHz, 5 s windows, **1280-d** embeddings. The published bundle is a TensorFlow SavedModel. Perch 2.0 is a later Google bioacoustics model (EfficientNet-B3, trained on Xeno-canto, iNaturalist, Animal Sound Archive, and FSD50K, including non-avian taxa). Its backbone consumes the same 5 s / 32 kHz contract and returns a **1536-d** embedding. A numerically checked ONNX export of the backbone is about 45 MB and ran here at roughly 30–40 ms per window on CPU.

`hrecos_ml.embeddings.SurfPerchTFEmbedder` will load a SurfPerch SavedModel if TensorFlow is installed. It was not executed in this run. `scripts/download_data.py --surfperch` fetches the 128 MB Zenodo zip and does not unpack it into git.

## Labels

Training classes are `bass_spawning_splash`, the three other fish sounds, `boat`, `train`, `rain`, `wave_slap`, and `background`. At inference, `train`, `rain`, and `wave_slap` are written as `unknown`. Plain `background` is not written at all. A steady mains hum is written as `unknown` by the pre-filter, not by the probe. A window is kept when its winning class is in the emitted set and its probability is at least 0.5, and a sturgeon winner also has to pass the low-band check.

`bass_spawning_splash` is a surface splash from a striped bass spawning rock fight (several males bumping a female at the surface), not a vocalization. `species.soniferous` for `striped_bass` stays false. No peer-reviewed spectrum of that splash was found. The synthetic hits follow generic splash physics: a short broadband impact plus a damped bubble (Franz 1959, JASA 31:1080). Spawning at or near the surface, often near 15–20 °C within a wider 10–23 °C range, is in Setzler et al. 1980, NOAA Technical Report NMFS Circular 433. Hudson egg distributions in Secor et al. 2020 (PLOS ONE 15(11):e0242797) put spawning reaches upriver of Kingston and through the West Point–Poughkeepsie stretch. Evening and night are when several rivers concentrate the behavior; that clock time is not an audio feature and is not a field on the detection row.

Boat wake is constant, or stop-start over tens of seconds to minutes, often with engine rumble before the wash. Spawning splashes are short impulsive bursts in clusters. Because the probe only sees 5 s, `detect()` runs `hrecos_ml.temporal` on buffers of at least 30 s. Over about 90 s of envelope it measures burst duration, duty cycle, and the gaps between bursts. A splash label that sits on an elevated block of at least 8 s, or anywhere between two such blocks, is rewritten to `boat`. A `boat` label that is not in that kind of wash is dropped, so a splash bout does not keep a stray boat row. Buffers shorter than 30 s are not gated.

Rain is a stationary field of small-drop impacts with a type-I bubble tone near 15 kHz (Nystuen 1986, JASA 79:972; Medwin, Nystuen, Jacobus, Ostwald, and Snyder 1992, JASA 92:1613). Wave slap is a quasi-periodic low-frequency thump. Both are training negatives and collapse to `unknown`.

| Detection label | `species_id` | Organism | What the synthesizer used |
| --- | --- | --- | --- |
| `bass_spawning_splash` | `striped_bass` | *Morone saxatilis* | broadband hits of 40–280 ms, a few per 5 s window; no measured bass spectrum |
| `sturgeon_thunder` | `atlantic_sturgeon` | *Acipenser oxyrinchus* | 10–100 Hz, peak near 44 Hz, bout about 1.9 s (Cohen et al. 2025, [doi:10.3354/esr01429](https://doi.org/10.3354/esr01429)) |
| `drum_knock` | `freshwater_drum` | *Aplodinotus grunniens* | knock train centered near 400 Hz |
| `toadfish_boatwhistle` | `oyster_toadfish` | *Opsanus tau* | tonal boatwhistle, fundamental roughly 110–240 Hz plus harmonics |
| `boat` | null | vessel | engine line that is not 60 Hz, or a 5 s crop of a long stop-start wake |
| `unknown` | null | train, rain, wave slap, steady 60 Hz hum, or other non-target | |

`species_id` is the primary key of `public.species` in `supabase/seed.sql`. River herring is seeded and is not a detection label.

`freq_low_hz` and `freq_high_hz` on a detection are the 10th and 90th percentiles of spectral energy from 10 to 4000 Hz on the winning window. They are measured from the audio. The bands above are not copied into those fields.

## What was trained

The committed weights (`0.2.1`) were fit only on synthetic clips from `hrecos_ml.synthesize`. FishSounds is CC BY-NC 4.0, so a probe trained on those files is not in the git tree. Real recordings are an external check, plus a leave-one-file-out probe that is fit in memory and discarded.

Context classes (bass, boat, train, rain, wave slap, background) follow the 0.2.0 random stream, so the bass examples and the wake negatives stay the ones the splash gate was checked against. Hum clips are drawn and thrown away so that stream does not shift; they are not rows in the fit. Sturgeon, drum, and toadfish are replaced with the distant-engine mix (fixed seeds 1–6). Each clip is 5 s at 32 kHz, pink noise at a random SNR from −2 to 16 dB, and a weak harmonic hum under every clip. Train: 48 per class, context seed `20260311` (432 clips). Test: 24 per class, context seed `20260917` (216 clips). The probe is `StandardScaler` plus L2 logistic regression (`C=1`, `class_weight="balanced"`).

Package versions for that fit: Python 3.12.3, numpy 2.5.4, scipy 1.18.1, scikit-learn 1.9.1, onnxruntime 1.31.1, onnx 1.23.2.

## Synthetic test (deployed Perch probe)

Rows of the confusion matrix are the true class, columns the predicted class, in priority order: bass splash, sturgeon, drum, toadfish, boat, train, rain, wave slap, background.

|  | bass | sturgeon | drum | toadfish | boat | train | rain | wave | background |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bass | 24 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| sturgeon | 0 | 23 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| drum | 0 | 0 | 24 | 0 | 0 | 0 | 0 | 0 | 0 |
| toadfish | 0 | 0 | 0 | 24 | 0 | 0 | 0 | 0 | 0 |
| boat | 0 | 0 | 0 | 0 | 24 | 0 | 0 | 0 | 0 |
| train | 0 | 0 | 0 | 0 | 0 | 24 | 0 | 0 | 0 |
| rain | 0 | 0 | 0 | 0 | 0 | 0 | 24 | 0 | 0 |
| wave | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 | 0 |
| background | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 |

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| bass_spawning_splash | 1.0000 | 1.0000 | 1.0000 | 24 |
| sturgeon_thunder | 1.0000 | 0.9583 | 0.9787 | 24 |
| drum_knock | 1.0000 | 1.0000 | 1.0000 | 24 |
| toadfish_boatwhistle | 1.0000 | 1.0000 | 1.0000 | 24 |
| boat | 0.9600 | 1.0000 | 0.9796 | 24 |
| train | 1.0000 | 1.0000 | 1.0000 | 24 |
| rain | 1.0000 | 1.0000 | 1.0000 | 24 |
| wave_slap | 1.0000 | 1.0000 | 1.0000 | 24 |
| background | 1.0000 | 1.0000 | 1.0000 | 24 |

The other two heads, same split:

| Head | Features | Accuracy | Macro-F1 |
| --- | ---: | ---: | ---: |
| Perch 2.0 (deployed) | 1536 | 0.9954 | 0.9954 |
| low-band descriptor | 26 | 0.9954 | 0.9954 |
| Perch + low-band | 1562 | 1.0000 | 1.0000 |

Sliding-window check on synthetic scenes (a 5 s clip mixed into 15 s of synthetic background; 8 scenes per class). These buffers are shorter than 30 s, so the splash and boat gates do not run. The sturgeon band check does run. A hit is a detection of the mapped label overlapping that 5 s span.

| Class | Detection label | Hits | Median absolute start error (s) |
| --- | --- | ---: | ---: |
| bass_spawning_splash | bass_spawning_splash | 8/8 | 3.29 |
| sturgeon_thunder | sturgeon_thunder | 5/8 | 2.09 |
| drum_knock | drum_knock | 8/8 | 2.82 |
| toadfish_boatwhistle | toadfish_boatwhistle | 8/8 | 1.42 |
| boat | boat | 8/8 | 1.84 |
| train | unknown | 8/8 | 3.52 |
| hum_60hz | unknown | 8/8 | 2.38 |
| rain | unknown | 8/8 | 3.92 |
| wave_slap | unknown | 8/8 | 2.62 |

Six synthetic background-only scenes produced a detection in **4/6**, all of them `boat`. The sturgeon scene hit rate of 5/8 is below the `0.1.0` figure of 7/8. The real supplements are the check that was required, and both are detected.

### Stop-start wakes and splash bouts

Eight 90 s stop-start wakes and eight 90 s splash bouts. A file counts if `detect()` emits the label anywhere.

| Sequence | Splash, gate off | Splash, gate on | Boat, gate off | Boat, gate on |
| --- | ---: | ---: | ---: | ---: |
| stop-start wake | 0/8 | 0/8 | 8/8 | 8/8 |
| splash bout | 8/8 | 8/8 | 0/8 | 0/8 |

On this draw the 5 s probe already emits no `boat` on the splash bouts. The gate still drops a boat label that is not sitting on a long wash, which is what turned the earlier 6/8 into a rule instead of a lucky split.

## Real recordings

Every download in the earlier run succeeded and was reused. The log is [`artifacts/data_access.json`](artifacts/data_access.json). Audio stays in `ml/data/` and is gitignored. Nothing here is a striped bass splash.

**FishSounds** ([doi:10.5683/SP2/TACOUX](https://doi.org/10.5683/SP2/TACOUX), Borealis, CC BY-NC 4.0). The Dataverse dataset has freshwater drum and toadfish-like boatwhistles. It does not have Atlantic sturgeon or oyster toadfish. Clips used:

- *Aplodinotus grunniens* drum calls, Rountree 2017, file ids 200686, 200719, 200764, 200676
- *Opsanus beta* (gulf toadfish, not *O. tau*) complex call, Looby 2022, file id 843171, labeled `toadfish_boatwhistle` as a proxy
- *Opsanus beta* grunt, file id 843165, left unscored
- *Halobatrachus didactylus* (Lusitanian toadfish) boatwhistle, Amorim 2008, file id 200588, also a proxy

Do not redistribute those wav files. Attribution: Looby, A., Riera, A., Vela, S., Cox, K., Bravo, S., Rountree, R., Juanes, F., Reynolds, L. K., and Martin, C. W. (2021). FishSounds Website Data Repository. https://doi.org/10.5683/SP2/TACOUX, Borealis, V10.

**Sturgeon exemplars.** Supplementary audio of Cohen et al. 2025, Endangered Species Research, [doi:10.3354/esr01429](https://doi.org/10.3354/esr01429): `n058p001_AS1.mp3` (wild thunder) and `n058p001_AS2.mp3` (captive thunder), from `https://www.int-res.com/articles/suppl/`. Not redistributed.

**NOAA NCEI** bucket `gs://noaa-passive-bioacoustic/`. For background, the first 12 MB of two Hudson files were fetched and ffmpeg decoded the first 20 s:

- `cornell/audio/noaa_nerrs/as/noaa-nerrs_hudsonriver_2023-2024_as_02/audio/144488Hudson_024K_AS02_ST300-5683_20210424_090503Zm0400.flac`
- `cornell/audio/noaa_nerrs/as/noaa-nerrs_hudsonriver_2023-2024_as_05/audio/144488Hudson_024K_AS05_ST300-5683_20210701_203738Zm0400.flac`

Center-window prediction of the deployed probe (one 5 s window per file, not sliding):

| File | Reference | Prediction | Confidence |
| --- | --- | --- | ---: |
| 200686 drum call 1 | drum_knock | toadfish_boatwhistle | 0.581 |
| 200719 drum call 2 | drum_knock | drum_knock | 0.586 |
| 200764 drum call 3 | drum_knock | drum_knock | 0.698 |
| 200676 drum chorus | drum_knock | sturgeon_thunder | 0.957 |
| 843171 *O. beta* complex call | toadfish_boatwhistle | toadfish_boatwhistle | 0.962 |
| 843165 *O. beta* grunt | unscored | bass_spawning_splash | 0.324 |
| 200588 *H. didactylus* boatwhistle | toadfish_boatwhistle | toadfish_boatwhistle | 0.963 |
| AS1 wild sturgeon | sturgeon_thunder | sturgeon_thunder | 0.950 |
| AS2 captive sturgeon | sturgeon_thunder | sturgeon_thunder | 0.994 |
| Hudson AS02 excerpt | background | boat | 0.294 |
| Hudson AS05 excerpt | background | boat | 0.716 |

`detect()` on the whole file:

- AS1: `sturgeon_thunder` 0.00–7.00 s, confidence 0.974, band 25.6–91.4 Hz, `atlantic_sturgeon`.
- AS2: `sturgeon_thunder` 0.00–6.00 s, confidence 0.986, band 25.2–1260.4 Hz, `atlantic_sturgeon`.
- Drum calls 2 and 3 are `drum_knock` (`freshwater_drum`). Call 1 is `toadfish_boatwhistle` (0.581). The chorus produces no row. The center-window sturgeon call does not pass the 10–100 Hz check.
- Both toadfish proxies are `toadfish_boatwhistle`. No `bass_spawning_splash` row on any of these files. The grunt is under the 0.5 threshold (0.324).
- Hudson AS02: `boat` 9.00–19.00 s (0.776). Hudson AS05: `boat` 0.00–20.00 s (0.947). Both excerpts are 20 s, under the 30 s gate.

Leave-one-file-out on the Perch features: **7/8** correct. The miss is drum call 1, predicted `toadfish_boatwhistle` (0.506). Both sturgeon files are `sturgeon_thunder` in this setting (0.710 and 0.998). The chorus is `drum_knock` (0.736) once the other drum clips are in the fold. That is still a handful of files, not a validation set.

## Cornell / Hudson River NERR

The recording set to train on next is the annotated Hudson River passive-acoustic collection associated with the NERRS project (Rice and colleagues; NOAA-NERRS Hudson River 2023–2024). The NERRS data description tells users to reach the archive through the [NCEI passive acoustic viewer](https://www.ncei.noaa.gov/maps/passive-acoustic-data/) and `pad.info@noaa.gov`. As of this run the raw 24 kHz FLAC is also listable at `gs://noaa-passive-bioacoustic/cornell/audio/noaa_nerrs/`. Filenames are not call labels. A labeled subset, including an actual striped bass rock-fight splash, is still the right thing to request before replacing the edge detector.

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

`detect` times are seconds from the start of the buffer. `to_detection_rows` turns them into `public.detections` objects. Those objects validate against `contracts/detections.schema.json`.

Each event:

```text
start_time, end_time          seconds from the start of audio
label                         bass_spawning_splash, sturgeon_thunder, drum_knock,
                              toadfish_boatwhistle, boat, or unknown
species_id                    species-table slug, or None for boat and unknown
confidence                    probability of the winning training class,
                              or the 60 Hz line share for a mains-hum window
freq_low_hz, freq_high_hz     measured energy percentiles
model_name, model_version     hrecos-fish-probe, 0.2.1
```

Audio is resampled to 32 kHz. Windows are 5 s with a 1 s hop. A steady 60 Hz line is `unknown` before the probe. A sturgeon winner that is not an impulsive 10–100 Hz bout is dropped. On buffers of at least 30 s, splash labels inside a sustained or stop-start wash become `boat`, and boat labels outside that wash are dropped. Pass `temporal_gate=False` to keep those context edits off. The Perch ONNX file is not in git. `detect` looks for `ml/data/models/perch_v2_backbone.onnx`.

## Raspberry Pi

The linear head is exported two ways:

- `artifacts/hrecos-fish-probe/0.2.1/probe.npz`, loaded by NumPy (no pickle)
- `artifacts/hrecos-fish-probe/0.2.1/probe.onnx`, a Gemm plus Softmax (`features` float32 `[batch, 1536]` to `probabilities`)

On a Pi, run the backbone with the TFLite file from the same Hugging Face repo (`biodiversica/Perch-onnx-backbone`, file `perch_v2_backbone.tflite`, about 43 MB) and then either ONNX Runtime or NumPy for the head. `scripts/download_data.py --tflite` fetches that file. This run did not execute TFLite.

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

`tests/test_real_audio.py` runs the sturgeon supplements and the drum clips when they are on disk, and skips when they are not. It fails if either sturgeon file has no `sturgeon_thunder` detection, if drum calls 2 or 3 have no `drum_knock`, or if those fish files emit `bass_spawning_splash`.

| Script | Role |
| --- | --- |
| `scripts/download_data.py` | Perch ONNX, FishSounds wavs, sturgeon mp3s, Hudson excerpts |
| `scripts/synthesize_data.py` | Synthetic train and test wavs |
| `scripts/compute_embeddings.py` | Perch and low-band matrices |
| `scripts/train.py` | Fit probes, write `0.2.1` |
| `scripts/evaluate.py` | Confusion matrix, real files, event timing, wake vs splash sequences |
| `scripts/export_model.py` | Rewrite the ONNX head |

`ml/data/` and `ml/artifacts/cache/` are gitignored. The small probe, metrics, and the download log are not.

## What this does not show

Bass precision of 1.0000 is on synthetic splashes. No rock-fight recording was in the fit or the external check. The low-band head would call real thunder a bass splash, which is why it is not deployed. Synthetic sturgeon scenes are detected in 5 of 8 cases. The drum chorus center window is still nearest sturgeon until the band check throws it out. Annotated river audio is the next training set.
