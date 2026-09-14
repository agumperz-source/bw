#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RANKS = "AKQJT98765432"
HCP = {"A": 4, "K": 3, "Q": 2, "J": 1}
SEED = 20260913
DEALS = 250_000


def generate_deals(count: int, seed: int) -> list[list[list[tuple[int, str]]]]:
    rng = random.Random(seed)
    deck = [(suit, rank) for suit in range(4) for rank in RANKS]
    deals = []
    for _ in range(count):
        cards = deck.copy()
        rng.shuffle(cards)
        deals.append([cards[i * 13 : (i + 1) * 13] for i in range(4)])
    return deals


def shape(hand: list[tuple[int, str]]) -> tuple[int, int, int, int]:
    lengths = [0, 0, 0, 0]
    for suit, _rank in hand:
        lengths[suit] += 1
    return tuple(lengths)


def hcp(hand: list[tuple[int, str]]) -> int:
    return sum(HCP.get(rank, 0) for _suit, rank in hand)


def controls(hand: list[tuple[int, str]]) -> int:
    lengths = shape(hand)
    total = 0
    for suit, rank in hand:
        if rank == "A":
            total += 2
        elif rank == "K" and lengths[suit] > 1:
            total += 1
    return total


def flannery_bucket(hand: list[tuple[int, str]]) -> str | None:
    spades, hearts, _diamonds, _clubs = shape(hand)
    points = hcp(hand)
    if (spades, hearts) == (5, 6):
        return "5S-6H" if 8 <= points <= 10 and controls(hand) >= 2 else None
    if (spades, hearts) == (4, 6):
        return "4S-6H" if 9 <= points <= 12 else None
    if (spades, hearts) == (4, 5):
        return "4S-5H" if 11 <= points <= 15 else None
    return None


def partner_index(seat: int) -> int:
    return (seat + 2) % 4


def responder_hcp_bucket(points: int) -> str:
    if points <= 4:
        return "0-4"
    if points <= 7:
        return "5-7"
    if points <= 9:
        return "8-9"
    if points <= 12:
        return "10-12"
    return "13+"


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> dict[str, float]:
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return {"low": center - margin, "high": center + margin}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def add(counter: Counter[str], label: str) -> None:
    counter[label] += 1


def run() -> tuple[dict, str]:
    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    deals = generate_deals(DEALS, SEED)
    n = 0
    counts: Counter[str] = Counter()

    for deal in deals:
        for seat, opener in enumerate(deal):
            opener_bucket = flannery_bucket(opener)
            if not opener_bucket:
                continue
            responder = deal[partner_index(seat)]
            os, oh, _od, _oc = shape(opener)
            rs, rh, _rd, _rc = shape(responder)
            responder_points = hcp(responder)
            heart_fit = oh + rh
            spade_fit = os + rs
            n += 1

            add(counts, f"opener_shape:{opener_bucket}")
            add(counts, f"responder_hearts:{rh if rh < 4 else '4+'}")
            add(counts, f"responder_spades:{rs if rs < 4 else '4+'}")
            add(counts, f"heart_fit:{oh}-{rh}")
            add(counts, f"spade_fit:{os}-{rs}")
            add(counts, f"responder_hcp:{responder_hcp_bucket(responder_points)}")
            if rh >= 3:
                add(counts, "condition:responder_3plus_hearts")
            if rs >= 4:
                add(counts, "condition:responder_4plus_spades")
            if heart_fit >= 8:
                add(counts, "condition:heart_fit_8plus")
            if spade_fit >= 8:
                add(counts, "condition:spade_fit_8plus")
            if heart_fit < 8 and spade_fit < 8:
                add(counts, "condition:no_8card_major_fit")
            if responder_points >= 8:
                add(counts, "condition:responder_8plus_hcp")
            if responder_points >= 10:
                add(counts, "condition:responder_10plus_hcp")
            if responder_points >= 13:
                add(counts, "condition:responder_13plus_hcp")

    rows = []
    for key, count in sorted(counts.items()):
        category, bucket = key.split(":", 1)
        interval = wilson(count, n)
        rows.append({"category": category, "bucket": bucket, "count": count, "proportion": count / n, "ci_low": interval["low"], "ci_high": interval["high"]})

    output = "category,bucket,count,proportion,ci_low,ci_high\n"
    for row in rows:
        output += f"{row['category']},{row['bucket']},{row['count']},{row['proportion']},{row['ci_low']},{row['ci_high']}\n"

    summary = {
        "schema_version": 1,
        "research_id": "RQ2",
        "status": "complete",
        "run_started_at": started_at,
        "run_finished_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.perf_counter() - started,
        "seed": SEED,
        "deal_count": DEALS,
        "qualifying_flannery_openers": n,
        "method": "For each qualifying Flannery hand in the same 250,000 random deals used by RQ1, treat the opposite hand as responder and tabulate major-suit fits and responder strength.",
        "confidence_interval": {"level": 0.95, "method": "Wilson score interval"},
        "headline_results": {
            "heart_fit_8plus": {"count": counts["condition:heart_fit_8plus"], "proportion": counts["condition:heart_fit_8plus"] / n, "ci": wilson(counts["condition:heart_fit_8plus"], n)},
            "spade_fit_8plus": {"count": counts["condition:spade_fit_8plus"], "proportion": counts["condition:spade_fit_8plus"] / n, "ci": wilson(counts["condition:spade_fit_8plus"], n)},
            "no_8card_major_fit": {"count": counts["condition:no_8card_major_fit"], "proportion": counts["condition:no_8card_major_fit"] / n, "ci": wilson(counts["condition:no_8card_major_fit"], n)},
            "responder_8plus_hcp": {"count": counts["condition:responder_8plus_hcp"], "proportion": counts["condition:responder_8plus_hcp"] / n, "ci": wilson(counts["condition:responder_8plus_hcp"], n)},
            "responder_10plus_hcp": {"count": counts["condition:responder_10plus_hcp"], "proportion": counts["condition:responder_10plus_hcp"] / n, "ci": wilson(counts["condition:responder_10plus_hcp"], n)},
            "responder_13plus_hcp": {"count": counts["condition:responder_13plus_hcp"], "proportion": counts["condition:responder_13plus_hcp"] / n, "ci": wilson(counts["condition:responder_13plus_hcp"], n)},
        },
        "counts": dict(sorted(counts.items())),
        "evidence": {"output_files": ["summary.json", "results.csv"], "sha256": {"results.csv": sha256_text(output)}},
        "runtime": {"python_version": sys.version.split()[0]},
    }
    return summary, output


def main() -> int:
    summary, csv_text = run()
    out = Path(__file__).parent
    (out / "results.csv").write_text(csv_text, encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary["headline_results"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
