# RQ01 Flannery Frequency

This directory is the research record for the first Flannery frequency study.

The study asks how often a randomly dealt hand qualifies for the proposed Flannery 2♦ opening, how those qualifying hands break down by shape and strength, and how much of the ordinary 1♥ opening population Flannery removes.

## Files

- `question.md` records the research question and intended outputs.
- `config.json` records the seed, sample-size placeholder, Flannery-definition placeholder, ordinary 1♥ baseline placeholder, DDS provenance, harness provenance, and confidence interval placeholder.
- `run.py` is a scaffold for the eventual frequency/classification runner. It imports the validated harness utilities but will not run until the definition fields are frozen.
- `summary.json` is the structured result template to be filled by the eventual run.

## Reproducibility standard

Before this experiment is run, `config.json` must state the exact sample size, inclusion rules, baseline 1♥ definition, and confidence interval method. A publishable run should write machine-readable results, preserve enough metadata to regenerate the sample from the same seed, and record hashes for any evidence files used in the book or tracker.

Do not treat interim console output as evidence. The durable record should be the committed configuration, generated summary, and any output tables created by the final runner.
