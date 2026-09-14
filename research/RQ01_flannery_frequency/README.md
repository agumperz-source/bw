# RQ01 Flannery Frequency

This directory is the research record for the first Flannery frequency study.

The study asks how often a randomly dealt hand qualifies for the proposed Flannery 2♦ opening, how those qualifying hands break down by shape and strength, and how much of the ordinary 1♥ opening population Flannery removes.

## Definition

For this first simulation, a hand qualifies for Flannery only with one of these major-suit patterns, with hearts longer than spades:

- 5S-6H: 8-10 HCP and 2+ controls.
- 4S-6H: 9-12 HCP.
- 4S-5H: 11-15 HCP.

Controls count ace = 2 and king = 1, except a singleton king does not count as a control.

The ordinary 1♥ baseline is implemented as 5+ hearts and 11-21 HCP. This is the agreed first-simulation approximation of "5+ hearts, 11-21 HCP, not eligible for a stronger opening, with no special exclusions beyond HCP and heart length."

## Files

- `question.md` records the research question and intended outputs.
- `config.json` records the seed, sample size, frozen first-simulation definitions, DDS provenance, harness provenance, and confidence interval method.
- `run.py` is the reproducible Monte Carlo runner.
- `summary.json` is the structured result file from the committed run.
- `results.csv` contains aggregate shape, strength, and minimum-subset buckets.

## Result

The committed run used 250,000 random deals, or 1,000,000 hands, with seed `20260913`.

It found 9,517 qualifying Flannery hands, or 0.9517% of random hands. That is about one qualifying hand per 105.1 hands. The Wilson 95% confidence interval is 0.9329% to 0.9709%.

Among ordinary 1♥ openings under the baseline, Flannery removed 8,286 of 76,173 hands, or 10.88%. The Wilson 95% confidence interval is 10.66% to 11.10%.

Of the 9,517 qualifying Flannery hands, 3,989 are minimum hands under the working definition: 4S-5H-2D-2C with 11-13 HCP, or 4S-5H-1D-3C / 4S-5H-3D-1C with 11-12 HCP. That is 41.91% of qualifying Flannery hands.

Minimum-hand breakdown by shape:

- 4S-5H-2D-2C: 2,091.
- 4S-5H-1D-3C: 945.
- 4S-5H-3D-1C: 953.

Minimum-hand breakdown by strength:

- 11 HCP: 1,813.
- 12 HCP: 1,593.
- 13 HCP: 583.

## Reproducibility standard

The durable record is the committed configuration, runner, summary, and aggregate CSV. DDS was not used for this experiment because RQ1 is a hand-frequency/classification study, not a double-dummy study.
