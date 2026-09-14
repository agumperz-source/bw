# RQ02 Flannery Fit Landscape

This directory records the second Flannery Monte Carlo study.

## Question

After a qualifying Flannery 2♦ opening, what major-suit fit and responder-strength landscape does opener's partner actually hold?

## Method

The run uses the same seed (`20260913`) and 250,000 random deals as RQ1. Each qualifying Flannery hand is treated as opener, and the opposite hand in the same deal is treated as responder.

This produced 9,517 qualifying Flannery opener/responder pairs.

## Headline Results

- 8+ card heart fit: 5,678 of 9,517 = 59.66% (95% CI 58.67% to 60.64%).
- 8+ card spade fit: 3,228 of 9,517 = 33.92% (95% CI 32.97% to 34.88%).
- No 8-card major fit: 2,144 of 9,517 = 22.53% (95% CI 21.70% to 23.38%).
- Responder has 8+ HCP: 6,322 of 9,517 = 66.43%.
- Responder has 10+ HCP: 4,458 of 9,517 = 46.84%.
- Responder has 13+ HCP: 1,936 of 9,517 = 20.34%.

## Design Consequence

Responder will often have a heart fit, but not so often that the structure can assume hearts are always right. About one third of auctions include an 8+ card spade fit, and about one quarter have no 8-card major fit. A practical response structure needs to expose heart support, find spades, and retain a path for no-major-fit hands.

## Files

- `question.md`: research question and intended outputs.
- `config.json`: fixed parameters and method.
- `run.py`: reproducible runner.
- `summary.json`: structured results.
- `results.csv`: aggregate fit, length, and responder-strength buckets with Wilson intervals.
