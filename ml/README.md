# Hudson River fish-sound baseline

Offline classifier for hydrophone audio, meant to stand in for a rule-based detector on an edge node. It freezes Google's **Perch 2.0** embedding model and trains a logistic-regression probe on top. The run below is CPU-only (ONNX Runtime). No metric in this file was typed in by hand; they are the numbers in [`artifacts/hrecos-fish-probe/0.1.0/metrics.json`](artifacts/hrecos-fish-probe/0.1.0/metrics.json) from the run on 2026-11-03.

This repository does not yet have a `detections` table. The probe metadata and every returned event use the field names that table would store: `model_name`, `model_version`, and `label` restricted to `sturgeon_thunder`, `drum_knock`, `toadfish_boatwhistle`, `boat`, and `unknown`.

## Result in one paragraph

On a held-out synthetic test set (24 clips per class, 168 clips), the deployed Perch probe has accuracy **0.9464** (159/168) and macro-F1 **0.9454**. The same head, applied to real audio it was not trained on, labels both Atlantic sturgeon supplementary clips as `sturgeon_thunder` when each file is reduced to one 5 s window (confidence 0.758 and 0.515). The sliding-window `detect()` API, which is what an edge node would call, keeps the wild clip (`n058p001_AS1.mp3`, 0.00–7.00 s, confidence 0.939, measured band 25.6–91.4 Hz) and misses the captive clip (`n058p001_AS2.mp3` comes back as `boat`). Two unlabeled 20 s Hudson River excerpts are not silent: one emits `unknown` (the 60 Hz class, collapsed) and the other emits `boat`. This is a baseline, not a replacement for the river detector yet.

A fixed low-frequency descriptor, trained the same way, scores **1.000** on the synthetic test and then calls both real sturgeon clips `drum_knock`, and both Hudson excerpts `drum_knock`. That perfect synthetic score is the synthesizer recognizing itself. It is reported so it is not mistaken for field accuracy. Concatenating it with Perch raises synthetic macro-F1 to **0.9818** and also misses both sturgeon clips, because the low-band block dominates the joint probe (mean absolute coefficient 0.0447 on the 26 low-band features versus 0.0118 on the 1536 Perch features, after standardization). The deployed artifact is therefore the Perch probe alone. Those 11 real files were inspected while making that choice, so they are not a locked test set.

## Why Perch 2.0, and not SurfPerch, for this run

SurfPerch (Zenodo [11060189](https://zenodo.org/records/11060189), Williams et al. 2024) is the closer pretraining domain: underwater sound, 32 kHz, 5 s windows, **1280-d** embeddings. The published bundle is a TensorFlow SavedModel. Perch 2.0 is a later Google bioacoustics model (EfficientNet-B3, trained on Xeno-canto, iNaturalist, Animal Sound Archive, and FSD50K, including non-avian taxa). Its backbone consumes the same 5 s / 32 kHz contract and returns a **1536-d** embedding. A numerically checked ONNX export of the backbone is about 45 MB and ran here at roughly 30–40 ms per window on CPU.

`hrecos_ml.embeddings.SurfPerchTFEmbedder` will load a SurfPerch SavedModel if TensorFlow is installed. It was not executed in this run. `scripts/download_data.py --surfperch` fetches the 128 MB Zenodo zip and does not unpack it into git.

## Labels

Training classes are the three fish sounds plus `boat`, `train`, `hum_60hz`, and `background`. At inference, `train` and `hum_60hz` are written as `unknown`. Plain `background` is not written at all, so a quiet buffer does not fill the table. A window is kept when its winning class is in that emitted set and its probability is at least 0.5.

| Detection label | `species_id` | Organism | Literature band used to synthesize it |
| --- | --- | --- | --- |
| `sturgeon_thunder` | `itis:624004` | *Acipenser oxyrinchus oxyrinchus* | 10–100 Hz, peak near 44 Hz, bout about 1.9 s (Cohen et al. 2025, [doi:10.3354/esr01429](https://doi.org/10.3354/esr01429)) |
| `drum_knock` | `itis:169364` | *Aplodinotus grunniens* | knock train centered near 400 Hz |
| `toadfish_boatwhistle` | `itis:164423` | *Opsanus tau* | tonal boatwhistle, fundamental roughly 110–240 Hz plus harmonics |
| `boat` | null | vessel | low-frequency engine line that is not 60 Hz, plus rumble |
| `unknown` | null | train, 60 Hz hum, or other non-target | |

ITIS serial numbers were read from the ITIS `searchByScientificName` service on 2026-11-03. Atlantic sturgeon is stored as the subspecies TSN 624004 (the species-level TSN is 553269).

`freq_low_hz` and `freq_high_hz` on a detection are the 10th and 90th percentiles of spectral energy from 10 to 4000 Hz on the winning window. They are measured from the audio. The literature bands above are not copied into those fields.

## What was trained

The committed weights (`model_name` `hrecos-fish-probe`, `model_version` `0.1.0`) were fit only on synthetic clips from `hrecos_ml.synthesize`. FishSounds is CC BY-NC 4.0, so a probe trained on those files is not in the git tree. Real recordings are an external check, plus a leave-one-file-out probe that is fit in memory and discarded.

Each synthetic clip is 5 s at 32 kHz. The target is mixed with pink noise at a random SNR from −2 to 16 dB, a weak 60 Hz line is added to every class (only `hum_60hz` is dominated by it), and about a third of fish clips also carry a quieter boat. Train split: 48 clips per class, seed `20260311` (336 clips). Test split: 24 per class, seed `20260917` (168 clips). The probe is `StandardScaler` plus L2 logistic regression (`C=1`, `class_weight="balanced"`).

Package versions for that fit: Python 3.12.3, numpy 2.5.4, scipy 1.18.1, scikit-learn 1.9.1, onnxruntime 1.31.1, onnx 1.23.2.

## Synthetic test (deployed Perch probe)

Rows of the confusion matrix are the true class, columns the predicted class, in this order: sturgeon, drum, toadfish, boat, train, hum, background.

|  | sturgeon | drum | toadfish | boat | train | hum | background |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sturgeon | 23 | 0 | 0 | 0 | 0 | 0 | 1 |
| drum | 0 | 24 | 0 | 0 | 0 | 0 | 0 |
| toadfish | 0 | 0 | 24 | 0 | 0 | 0 | 0 |
| boat | 0 | 0 | 0 | 22 | 0 | 2 | 0 |
| train | 0 | 0 | 0 | 0 | 24 | 0 | 0 |
| hum | 0 | 0 | 0 | 4 | 0 | 18 | 2 |
| background | 0 | 0 | 0 | 0 | 0 | 0 | 24 |

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| sturgeon_thunder | 1.0000 | 0.9583 | 0.9787 | 24 |
| drum_knock | 1.0000 | 1.0000 | 1.0000 | 24 |
| toadfish_boatwhistle | 1.0000 | 1.0000 | 1.0000 | 24 |
| boat | 0.8462 | 0.9167 | 0.8800 | 24 |
| train | 1.0000 | 1.0000 | 1.0000 | 24 |
| hum_60hz | 0.9000 | 0.7500 | 0.8182 | 24 |
| background | 0.8889 | 1.0000 | 0.9412 | 24 |

The other two heads, same split:

| Head | Features | Accuracy | Macro-F1 |
| --- | ---: | ---: | ---: |
| Perch 2.0 (deployed) | 1536 | 0.9464 | 0.9454 |
| low-band descriptor | 26 | 1.0000 | 1.0000 |
| Perch + low-band | 1562 | 0.9821 | 0.9818 |

Sliding-window check on synthetic scenes (a 5 s clip mixed into 15 s of synthetic background at a known offset; 8 scenes per class). A hit is a detection of the mapped label overlapping that 5 s span. Start error is coarse: the model sees 5 s windows on a 1 s hop.

| Class | Detection label | Hits | Median absolute start error (s) |
| --- | --- | ---: | ---: |
| sturgeon_thunder | sturgeon_thunder | 7/8 | 1.62 |
| drum_knock | drum_knock | 8/8 | 1.97 |
| toadfish_boatwhistle | toadfish_boatwhistle | 8/8 | 1.25 |
| boat | boat | 8/8 | 1.58 |
| train | unknown | 8/8 | 3.07 |
| hum_60hz | unknown | 8/8 | 2.57 |

Six synthetic background-only scenes produced a detection in **2/6**. The generator is the same family the probe was trained on, so these rates are a pipeline check.

## Real recordings

Every download in this run succeeded. The log is [`artifacts/data_access.json`](artifacts/data_access.json). Audio stays in `ml/data/` and is gitignored.

**FishSounds** ([doi:10.5683/SP2/TACOUX](https://doi.org/10.5683/SP2/TACOUX), Borealis, CC BY-NC 4.0). The Dataverse dataset has freshwater drum and toadfish-like boatwhistles. It does not have Atlantic sturgeon or oyster toadfish. Clips used:

- *Aplodinotus grunniens* drum calls, Rountree 2017, file ids 200686, 200719, 200764, 200676
- *Opsanus beta* (gulf toadfish, not *O. tau*) complex call, Looby 2022, file id 843171, labeled `toadfish_boatwhistle` as a proxy
- *Opsanus beta* grunt, file id 843165, left unscored
- *Halobatrachus didactylus* (Lusitanian toadfish) boatwhistle, Amorim 2008, file id 200588, also a proxy

Do not redistribute those wav files. Attribution: Looby, A., Riera, A., Vela, S., Cox, K., Bravo, S., Rountree, R., Juanes, F., Reynolds, L. K., and Martin, C. W. (2021). FishSounds Website Data Repository. https://doi.org/10.5683/SP2/TACOUX, Borealis, V10.

**Sturgeon exemplars.** Supplementary audio of Cohen et al. 2025, Endangered Species Research, [doi:10.3354/esr01429](https://doi.org/10.3354/esr01429): `n058p001_AS1.mp3` (wild thunder) and `n058p001_AS2.mp3` (captive thunder), from `https://www.int-res.com/articles/suppl/`. Not redistributed.

**NOAA NCEI** bucket `gs://noaa-passive-bioacoustic/`. The archive is public. Boat events are not labeled in the object names, and the Hudson files are multi-hundred-MB FLACs, so boat and train stay synthetic. For background, the first 12 MB of two files were fetched and ffmpeg decoded the first 20 s:

- `cornell/audio/noaa_nerrs/as/noaa-nerrs_hudsonriver_2023-2024_as_02/audio/144488Hudson_024K_AS02_ST300-5683_20210424_090503Zm0400.flac`
- `cornell/audio/noaa_nerrs/as/noaa-nerrs_hudsonriver_2023-2024_as_05/audio/144488Hudson_024K_AS05_ST300-5683_20210701_203738Zm0400.flac`

Center-window prediction of the deployed probe (one 5 s window per file, not sliding):

| File | Reference | Prediction | Confidence |
| --- | --- | --- | ---: |
| 200686 drum call 1 | drum_knock | toadfish_boatwhistle | 0.890 |
| 200719 drum call 2 | drum_knock | drum_knock | 0.621 |
| 200764 drum call 3 | drum_knock | drum_knock | 0.690 |
| 200676 drum chorus | drum_knock | hum_60hz | 0.805 |
| 843171 *O. beta* complex call | toadfish_boatwhistle | toadfish_boatwhistle | 0.941 |
| 843165 *O. beta* grunt | unscored | hum_60hz | 0.361 |
| 200588 *H. didactylus* boatwhistle | toadfish_boatwhistle | toadfish_boatwhistle | 0.994 |
| AS1 wild sturgeon | sturgeon_thunder | sturgeon_thunder | 0.758 |
| AS2 captive sturgeon | sturgeon_thunder | sturgeon_thunder | 0.515 |
| Hudson AS02 excerpt | background | hum_60hz | 0.737 |
| Hudson AS05 excerpt | background | background | 0.459 |

`detect()` on the whole file disagrees with that center window in a few places, because a different 5 s slice wins:

- AS1: `sturgeon_thunder` 0.00–7.00 s, confidence 0.939, band 25.6–91.4 Hz, `species_id` `itis:624004`, plus an overlapping `unknown` at 5.00–7.00 s (confidence 0.802).
- AS2: `boat` 3.00–6.00 s, confidence 0.997. The center-window sturgeon call does not survive the hop.
- Drum calls 2 and 3 are `drum_knock`. Call 1 is `toadfish_boatwhistle` (0.890). The chorus is mostly `unknown`, with a short `drum_knock` at the end (0.519).
- Both toadfish proxies come back as `toadfish_boatwhistle`. The Lusitanian toadfish file is a minute long and also produces `unknown` segments.
- The grunt produces no detection (its center-window hum probability is 0.361, under the 0.5 threshold).
- Hudson AS02: `unknown` 7–17 s and 18–20 s. Hudson AS05: `boat` 1–11 s and 13–20 s, plus `unknown`.

Leave-one-file-out on the Perch features (synthetic train, plus the other real fish clips, held-out file never seen): **6/8** correct. Misses: drum call 1 predicted `toadfish_boatwhistle` (0.555), and the *O. beta* complex call predicted `sturgeon_thunder` (0.544). Both sturgeon files are correct in this setting (0.943 and 0.690) once the other sturgeon clip is allowed into training. That is two examples, not a validation set.

## Cornell / Hudson River NERR

The recording set to train on next is the annotated Hudson River passive-acoustic collection associated with the NERRS project (Rice and colleagues; NOAA-NERRS Hudson River 2023–2024). The NERRS data description tells users to reach the archive through the [NCEI passive acoustic viewer](https://www.ncei.noaa.gov/maps/passive-acoustic-data/) and `pad.info@noaa.gov`. As of this run the raw 24 kHz FLAC is also listable at `gs://noaa-passive-bioacoustic/cornell/audio/noaa_nerrs/` (deployments `as`, `ich`, `pch`, `sch`, `ss`, `tch`). Filenames are not call labels. `cornell/products/detections/` in that bucket is a Gulf of Mexico sperm-whale table, not Hudson fish marks. A labeled subset is still the right thing to request from Cornell / Hudson River NERR before replacing the edge detector.

## Interface

```python
from hrecos_ml.infer import detect

events = detect(audio, sample_rate)  # samples, hertz
```

Each event:

```text
start_time, end_time          seconds from the start of audio
label                         one of the five detection labels
species_id                    ITIS id, or None for boat and unknown
confidence                    probability of the winning training class
freq_low_hz, freq_high_hz     measured energy percentiles
model_name, model_version     hrecos-fish-probe, 0.1.0
```

Audio is resampled to 32 kHz. Windows are 5 s with a 1 s hop, merged when the label matches. The Perch ONNX file is not in git. `detect` looks for `ml/data/models/perch_v2_backbone.onnx`.

## Raspberry Pi

The linear head is exported two ways:

- `artifacts/hrecos-fish-probe/0.1.0/probe.npz`, loaded by NumPy (no pickle)
- `artifacts/hrecos-fish-probe/0.1.0/probe.onnx`, a Gemm plus Softmax (`features` float32 `[batch, 1536]` to `probabilities`)

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
| `scripts/train.py` | Fit probes, write `0.1.0` |
| `scripts/evaluate.py` | Confusion matrix, real files, event timing |
| `scripts/export_model.py` | Rewrite the ONNX head |

`ml/data/` and `ml/artifacts/cache/` are gitignored. The small probe, metrics, and the download log are not.

## What this does not show

The synthetic classes were built from the same frequency story the low-band features measure, so a high synthetic score, especially 1.0, is not evidence about the Hudson. Perch is still a model whose frontend was designed for birds; getting both sturgeon center windows right is encouraging and is also n = 2. There is no labeled vessel or train audio in the training mix. The two Hudson excerpts already produce `boat` and `unknown` hits, which would be false rows in a detections table. Annotated river audio is the next training set, not more synthetic SNR.
