# Flannery Research Harness

This harness is the reproducible quantitative-analysis foundation for *Flannery for the 21st Century*.

## Pinned solver

The validation workflow uses the official `dds-bridge/dds` release tag **v3.1.0**. The workflow also records the exact upstream Git commit SHA in every validation run.

## What validation proves

A validation run generates 1,000 uniformly random complete bridge deals with Python's deterministic `random.Random` generator and seed `20260913`, solves the complete 5-strain x 4-declarer DDS table for every deal, and checks:

- identical deals are regenerated from the same seed;
- all 1,000 validation deals are unique;
- every DDS table has 5 strain rows and 4 declarer columns;
- all trick results are integers from 0 through 13;
- the first 10 deals agree between DDS `calc_dd_table` (binary-card input) and `calc_all_tables_pbn` (PBN batch input);
- the first 50 deals are identical with 1, 2, and 4 DDS worker threads;
- the first 25 deals preserve all DD values when all four hands are rotated one seat clockwise.

Before the harness validation, the workflow also runs DDS's own Python table and table-regression tests.

## Output files

`results/validation_deals.pbn` contains the exact validation sample. `results/validation_tables.csv` contains 20 DDS trick counts per deal in strain order spades, hearts, diamonds, clubs, notrump and seat order North, East, South, West. `results/validation_metadata.json` records solver provenance, seed, parameters, checks, elapsed time, and SHA-256 hashes. `results/VALIDATION_PASS.txt` is the compact audit record.

## Re-running

The canonical run is the GitHub Actions workflow `.github/workflows/flannery-dds-validation.yml`. It checks out DDS 3.1.0, uses the Bazel/Python toolchain pinned by that release, runs upstream regression tests, executes the 1,000-deal validation, and records the text outputs.

For later book studies, import the deal generator and DDS batch interface rather than changing the validation sample. Each research study should have its own seed, sample-size declaration, inclusion rules, output file, and metadata/hash record.

## Research standard

A Monte Carlo result should be framed so that it can contradict the hypothesis being tested. The harness records inputs and outputs so any reported percentage can be regenerated from the same sample rather than treated as a one-off calculation.
