#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
from typing import Any

RANKS = "AKQJT98765432"
HCP = {"A": 4, "K": 3, "Q": 2, "J": 1}
DEFAULT_CONFIG = Path(__file__).with_name("config.json")


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


def ordinary_one_heart(hand: list[tuple[int, str]]) -> bool:
    points = hcp(hand)
    return shape(hand)[1] >= 5 and 11 <= points <= 21


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> dict[str, float | None]:
    if total == 0:
        return {"low": None, "high": None}
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return {"low": center - margin, "high": center + margin}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(config: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str | int | float]]]:
    deal_count = int(config["deal_count"])
    seed = int(config["seed"])
    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    deals = generate_deals(deal_count, seed)

    total_hands = deal_count * 4
    flannery_count = 0
    one_heart_count = 0
    removed_count = 0
    shape_counts: Counter[str] = Counter()
    strength_counts: Counter[str] = Counter()

    for deal in deals:
        for hand in deal:
            bucket = flannery_bucket(hand)
            is_one_heart = ordinary_one_heart(hand)
            if bucket:
                flannery_count += 1
                shape_counts[bucket] += 1
                strength_counts[f"{hcp(hand)} HCP"] += 1
            if is_one_heart:
                one_heart_count += 1
                if bucket:
                    removed_count += 1

    finished_at = datetime.now(timezone.utc).isoformat()
    elapsed = time.perf_counter() - started
    p_flannery = flannery_count / total_hands
    p_removed = removed_count / one_heart_count

    rows: list[dict[str, str | int | float]] = []
    for label, count in sorted(shape_counts.items()):
        rows.append({"category": "shape", "bucket": label, "count": count, "proportion_of_flannery": count / flannery_count})
    for label, count in sorted(strength_counts.items(), key=lambda item: int(item[0].split()[0])):
        rows.append({"category": "strength", "bucket": label, "count": count, "proportion_of_flannery": count / flannery_count})

    summary: dict[str, Any] = {
        "schema_version": 1,
        "research_id": "RQ1",
        "status": "complete",
        "run_started_at": started_at,
        "run_finished_at": finished_at,
        "elapsed_seconds": elapsed,
        "deal_count": deal_count,
        "sample_size": total_hands,
        "seed": seed,
        "flannery_definition": config["flannery_definition"],
        "ordinary_one_heart_baseline": config["ordinary_one_heart_baseline"],
        "confidence_interval": config["confidence_interval"],
        "results": {
            "random_hand_frequency": {
                "qualifying_hands": flannery_count,
                "total_hands": total_hands,
                "proportion": p_flannery,
                "percentage": p_flannery * 100,
                "one_in_n_hands": 1 / p_flannery,
                "confidence_interval_95": wilson_interval(flannery_count, total_hands),
            },
            "shape_distribution": [
                {"shape": label, "count": count, "proportion_of_flannery": count / flannery_count}
                for label, count in sorted(shape_counts.items())
            ],
            "strength_distribution": [
                {"hcp": label, "count": count, "proportion_of_flannery": count / flannery_count}
                for label, count in sorted(strength_counts.items(), key=lambda item: int(item[0].split()[0]))
            ],
            "ordinary_one_heart_removed": {
                "removed_count": removed_count,
                "ordinary_one_heart_count": one_heart_count,
                "proportion": p_removed,
                "percentage": p_removed * 100,
                "confidence_interval_95": wilson_interval(removed_count, one_heart_count),
            },
        },
        "runtime": {"python_version": sys.version.split()[0]},
        "notes": [],
    }
    return summary, rows


def write_outputs(summary: dict[str, Any], rows: list[dict[str, str | int | float]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.csv"
    with results_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "bucket", "count", "proportion_of_flannery"])
        writer.writeheader()
        writer.writerows(rows)

    summary["evidence"] = {
        "output_files": ["summary.json", "results.csv"],
        "sha256": {
            "results.csv": sha256_text(results_path.read_text(encoding="utf-8")),
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    summary, rows = run(read_config(args.config))
    write_outputs(summary, rows, args.out)
    print(json.dumps(summary["results"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
