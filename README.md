# CascadeBalance

Implementation of **Public service calendars for loop-safe last-hop metadata equalization**.

Compiles public integer calendars with cyclic service windows and per-node capacity. Fixed outer slots serve one shared real/loop FIFO, or remain dummy slots.

## Install

Use Python 3.11 or newer.

```bash
git clone https://github.com/Hqa77880011/CascadeBalance.git
cd CascadeBalance
python -m venv .venv
```

Activate with `source .venv/bin/activate` on Linux/macOS or `.venv\Scripts\Activate.ps1` in PowerShell, then install.

```bash
python -m pip install -e .
```

## Data preparation

Public configuration fixes mixes, users, ticks, capacity, gap/quota, epochs and packet bytes. Private arrivals specify pair, time, deadline and loop/attack status.

```bash
python -m cascadebalance prepare --count 200 --seed 17 --output data/workload.jsonl
```

The generator creates finite workloads from the formal model. Each JSONL row is one scenario. `--count` controls corpus size and `--seed` controls generation. Imported cases use the same schema. Generate calibration and test scenarios independently.

## Execute and compare

```bash
python -m cascadebalance run --data data/workload.jsonl --output runs/main
python -m cascadebalance suite --data data/workload.jsonl --output runs/comparison
```

Select methods with `--methods`. sparse_public solves the calendar MILP; dense_public serves every pair; no_defense uses occupied slots; poisson_cover adds stochastic cover; queue_driven uses queue-dependent service.

## Evaluation and visualization

Real delivery, loop timeout TPR/FPR, byte ratio, scheduled bytes, mean/P95 waiting, expiry, CPU and trained association AUC.

Each method writes `records.jsonl` and `metrics.json` with means, sample standard deviations, usable counts and P50/P95/P99. Rates are fractions. Undefined conditional metrics remain unavailable. Method timers exclude reference scoring. RSS includes the Python runtime; serialized sizes measure JSON bytes.

```bash
python -m cascadebalance plot --inputs runs/comparison/sparse_public --output figures
```

Pass multiple method directories to compare them. Plotting writes `summary.csv` and metric PNGs.

## Implementation conventions

This is a discrete-event scheduler. Loop detection is the explicitly modeled timeout endpoint. Cryptographic indistinguishability requires a protocol-format encrypted forwarding layer. The calendar is checked before use and never receives private arrivals.

## Independent attacker training

Prepare and execute independent train, validation and test corpora with different seeds, then run:

```bash
python -m cascadebalance.attack --train runs/train/sparse_public/records.jsonl --validation runs/validation/sparse_public/records.jsonl --test runs/test/sparse_public/records.jsonl --output runs/attacker
```

The attacker selects logistic regression or ExtraTrees using validation AUC and reports held-out Top-1, balanced accuracy, AUC and validation-threshold TPR/FPR. Recorded data must use disjoint households/sessions. The fitted attacker is saved to `attacker.joblib`.


## Uncertainty and paired comparisons

```bash
python -m cascadebalance.statistics --records runs/main/sparse_public/records.jsonl --output results/intervals.json
```

Supply --reference with a matched record file for paired differences. Resampling uses independent case IDs, or explicit cluster IDs when provided. Repeated observations from one source unit must share cluster. Zero-event bounds refer to an event in an independent cluster.

## Fixed reproduction setting

Ideal opaque cells: 2 mixes x 2 users, 16-tick cyclic calendar, four epochs, capacity2, gap4/quota1, 512-byte cells. Independent train/validation/test episodes (seeds11/17/29) fit a held-out attacker for each registered defense.

The checked-in entry point fixes data seeds, methods, budgets and output paths. Inspect its commands without starting any computation:

```bash
python reproduce.py --plan
```

Remove `--plan` to execute the registered pipeline in a fresh output directory. The entry point calls the existing implementation; it does not insert paper results. Installation uses the package instructions above.
