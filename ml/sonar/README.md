# Synthetic sonar-track classifier

A prototype for the Hudson sonar track. It classifies simulated tracks of Atlantic sturgeon, striped bass, river herring, and American shad. Every number below is from that generator. None of it is a field result, and none of it was typed in by hand. The file [`artifacts/synthetic_metrics.json`](artifacts/synthetic_metrics.json) is what `scripts/evaluate.py` wrote. Re-run the script to replace it. Do not edit it.

Public labeled sonar sets, and why this code does not train on them, are in [`docs/sonar-track.md`](../../docs/sonar-track.md). The short version: Helminen and Linnansaari's pond ARIS sample contains striped bass and American shad ([figshare 14423630](https://doi.org/10.6084/m9.figshare.14423630)); the Normandy ARIS/DIDSON set ([Zenodo 5046707](https://doi.org/10.5281/zenodo.5046707)) is other species, including allis shad rather than American shad; CFC26 ([perona-lab/cfc26](https://huggingface.co/datasets/perona-lab/cfc26)) is detection, tracking, and counting, with no species labels for these four fish. No weights were fit on those files.

## What was fit

`sonar_node.simulate` drew tracks for `westpoint-cornwall` from 2026-03-01 through 2026-08-01, seed `20260311`, group-rate multiplier `0.35`. That was 62,798 tracks. The split is temporal: `start < 2026-06-01` is train (59,990 tracks), the rest is test (2,808 tracks). June and July are still inside the bass and sturgeon windows and at the tail of the shad and herring windows, so the test is not an empty season.

Features are the observed length, depth, speed, a surface flag, a surface-cluster flag, a school flag, log cluster size, and the day of year as sine and cosine. Truth species is the label. It is not a feature. The length-and-behavior rules do not see the day of year. The softmax does. A higher softmax score is not evidence that a linear model beats the rules on a river.

The head is multinomial logistic regression in NumPy, 400 steps, balanced class weights, fit seed 0. It abstains when the largest probability is below 0.45. `model_name` is `synthetic_softmax`, `model_version` is `0.1.0`. Weights are `artifacts/softmax_weights.npz`. The edge node loads them with `classifier.name: ml` and `entrypoint: hrecos_sonar.plugin:build_classifier` if `ml/sonar` is on `PYTHONPATH`.

`classify_frames` checks that the input is a float stack shaped `(n_frames, height, width)` and then raises `NotImplementedError`. There is no ARIS frame model in this package.

## Synthetic test

Accuracy is exact match with the generator's species. An abstention is a miss. Rules: **2,576 / 2,808 = 0.9174**, macro-F1 **0.9416**. Softmax: **2,708 / 2,808 = 0.9644**, macro-F1 **0.9469**.

The rules confusion (rows are truth, columns are atlantic sturgeon, striped bass, river herring, American shad, abstain):

|  | sturgeon | bass | herring | shad | abstain |
| --- | ---: | ---: | ---: | ---: | ---: |
| sturgeon | 97 | 0 | 0 | 0 | 0 |
| bass | 2 | 775 | 19 | 0 | 6 |
| herring | 0 | 0 | 533 | 5 | 31 |
| shad | 0 | 103 | 34 | 1171 | 32 |

Most of the rules' shad errors are the 103 tracks called striped bass. Those are the lone fish and the tracks whose school label was dropped: a 40–60 cm target without a school is allowed to be a bass. That is the overlap described in the research note, not a tuning target. Sturgeon in this draw are all inside 100–250 cm and are not the juveniles that would sit on top of large bass. The generator does not emit those juveniles, so a perfect sturgeon recall here does not survive contact with the river.

Regenerate:

```bash
cd ml/sonar
python3 scripts/evaluate.py
python3 -m pytest tests -q
```

The test refits the same split and checks that the committed accuracy still matches.
