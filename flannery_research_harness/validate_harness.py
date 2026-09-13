#!/usr/bin/env python3
"""Reproducible DDS3 validation harness for Flannery research."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Sequence

from dds3 import calc_all_tables_pbn, calc_dd_table

STRAINS = ("S", "H", "D", "C", "NT")
SEATS = ("N", "E", "S", "W")
RANKS = "AKQJT98765432"
RANK_VALUE = {str(n): n for n in range(2, 10)}
RANK_VALUE.update({"T": 10, "J": 11, "Q": 12, "K": 13, "A": 14})
DDS_MAX_TABLES = 40
DEFAULT_SEED = 20260913
DEFAULT_COUNT = 1000


def generate_deals(count: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    deck = [(suit, rank) for suit in range(4) for rank in RANKS]
    deals = []
    for _ in range(count):
        cards = deck.copy()
        rng.shuffle(cards)
        hands = [cards[i * 13:(i + 1) * 13] for i in range(4)]
        deals.append("N:" + " ".join(hand_to_pbn(hand) for hand in hands))
    return deals


def hand_to_pbn(hand: Sequence[tuple[int, str]]) -> str:
    holdings = [[] for _ in range(4)]
    for suit, rank in hand:
        holdings[suit].append(rank)
    pos = {rank: i for i, rank in enumerate(RANKS)}
    return ".".join("".join(sorted(h, key=pos.__getitem__)) for h in holdings)


def pbn_to_cards(pbn: str) -> list[list[int]]:
    prefix, body = pbn.split(":", 1)
    if prefix != "N":
        raise ValueError("Expected N-starting PBN")
    hands = body.split()
    if len(hands) != 4:
        raise ValueError("Expected four hands")
    result = []
    for hand in hands:
        holdings = hand.split(".")
        if len(holdings) != 4:
            raise ValueError(f"Bad hand: {hand}")
        masks = []
        for holding in holdings:
            mask = 0
            for rank in holding:
                mask |= 1 << RANK_VALUE[rank]
            masks.append(mask)
        result.append(masks)
    return result


def rotate_clockwise(pbn: str) -> str:
    prefix, body = pbn.split(":", 1)
    if prefix != "N":
        raise ValueError("Expected N-starting PBN")
    hands = body.split()
    if len(hands) != 4:
        raise ValueError("Expected four hands")
    return "N:" + " ".join([hands[3], hands[0], hands[1], hands[2]])


def solve_batches(deals: Sequence[str], batch_size: int, max_threads: int):
    if not 1 <= batch_size <= DDS_MAX_TABLES:
        raise ValueError(f"batch_size must be 1..{DDS_MAX_TABLES}")
    tables = []
    for start in range(0, len(deals), batch_size):
        chunk = list(deals[start:start + batch_size])
        result = calc_all_tables_pbn(
            chunk,
            mode=-1,
            trump_filter=[0, 0, 0, 0, 0],
            max_threads=max_threads,
        )
        if result["no_of_boards"] != len(chunk) or len(result["tables"]) != len(chunk):
            raise AssertionError("DDS batch result count mismatch")
        tables.extend(table["res_table"] for table in result["tables"])
    return tables


def validate_shape_and_range(tables) -> None:
    for board, table in enumerate(tables):
        if len(table) != 5 or any(len(row) != 4 for row in table):
            raise AssertionError(f"Board {board}: DD table is not 5x4")
        for row in table:
            for tricks in row:
                if not isinstance(tricks, int) or not 0 <= tricks <= 13:
                    raise AssertionError(f"Board {board}: invalid trick count {tricks!r}")


def validate_single_batch(deals, expected, count: int = 10) -> None:
    for i in range(min(count, len(deals))):
        single = calc_dd_table({"cards": pbn_to_cards(deals[i])})["res_table"]
        if single != expected[i]:
            raise AssertionError(f"Single/batch mismatch at board {i}")


def validate_threads(deals, expected, count: int = 50) -> None:
    sample = list(deals[:min(count, len(deals))])
    target = list(expected[:len(sample)])
    for threads in (1, 4):
        actual = solve_batches(sample, min(DDS_MAX_TABLES, len(sample)), threads)
        if actual != target:
            raise AssertionError(f"Thread determinism failed for max_threads={threads}")


def validate_rotation(deals, expected, count: int = 25) -> None:
    n = min(count, len(deals))
    rotated = [rotate_clockwise(deals[i]) for i in range(n)]
    actual = solve_batches(rotated, min(DDS_MAX_TABLES, n), 2)
    for i, (original, moved) in enumerate(zip(expected[:n], actual)):
        for strain in range(5):
            for old_seat in range(4):
                new_seat = (old_seat + 1) % 4
                if original[strain][old_seat] != moved[strain][new_seat]:
                    raise AssertionError(
                        f"Rotation mismatch board={i} strain={strain} seat={old_seat}"
                    )


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_outputs(out_dir: Path, deals, tables, metadata: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    deals_text = "\n".join(deals) + "\n"
    (out_dir / "validation_deals.pbn").write_text(deals_text, encoding="utf-8")

    columns = ["board", "pbn"] + [f"{strain}_{seat}" for strain in STRAINS for seat in SEATS]
    with (out_dir / "validation_tables.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for board, (pbn, table) in enumerate(zip(deals, tables)):
            row = {"board": board, "pbn": pbn}
            for strain_i, strain in enumerate(STRAINS):
                for seat_i, seat in enumerate(SEATS):
                    row[f"{strain}_{seat}"] = table[strain_i][seat_i]
            writer.writerow(row)

    table_text = json.dumps(tables, separators=(",", ":"), ensure_ascii=True)
    metadata = dict(metadata)
    metadata["deals_sha256"] = digest(deals_text)
    metadata["tables_sha256"] = digest(table_text)
    metadata["combined_sha256"] = digest(deals_text + "\n" + table_text)
    (out_dir / "validation_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "Flannery research harness validation: PASS",
        f"DDS tag: {metadata['dds_tag']}",
        f"DDS commit: {metadata['dds_commit']}",
        f"Deals: {metadata['deal_count']}",
        f"Seed: {metadata['seed']}",
        f"Deals SHA-256: {metadata['deals_sha256']}",
        f"Tables SHA-256: {metadata['tables_sha256']}",
        f"Combined SHA-256: {metadata['combined_sha256']}",
        "Checks: " + ", ".join(metadata["checks"]),
    ]
    (out_dir / "VALIDATION_PASS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--batch-size", type=int, default=DDS_MAX_TABLES)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.count <= 0:
        parser.error("--count must be positive")
    if not 1 <= args.batch_size <= DDS_MAX_TABLES:
        parser.error(f"--batch-size must be 1..{DDS_MAX_TABLES} (DDS CalcAllTables limit)")
    if args.threads <= 0:
        parser.error("--threads must be positive")

    started = time.perf_counter()
    deals = generate_deals(args.count, args.seed)
    if deals != generate_deals(args.count, args.seed):
        raise AssertionError("Deal generator is not deterministic")
    if len(set(deals)) != len(deals):
        raise AssertionError("Duplicate deals in validation sample")

    tables = solve_batches(deals, args.batch_size, args.threads)
    validate_shape_and_range(tables)
    validate_single_batch(deals, tables)
    validate_threads(deals, tables)
    validate_rotation(deals, tables)

    elapsed = time.perf_counter() - started
    metadata = {
        "schema_version": 1,
        "status": "PASS",
        "dds_tag": os.environ.get("DDS_TAG", "unknown"),
        "dds_commit": os.environ.get("DDS_GIT_SHA", "unknown"),
        "deal_count": args.count,
        "seed": args.seed,
        "batch_size": args.batch_size,
        "primary_max_threads": args.threads,
        "python_version": sys.version.split()[0],
        "elapsed_seconds": round(elapsed, 6),
        "checks": [
            "generator_reproducibility",
            "sample_uniqueness",
            "table_shape_5x4",
            "trick_range_0_13",
            "single_vs_batch_parity_10",
            "thread_determinism_50_1v2v4",
            "clockwise_rotation_symmetry_25",
        ],
    }
    write_outputs(args.out, deals, tables, metadata)
    print(json.dumps(metadata, indent=2, sort_keys=True))
    print(f"PASS: {args.count} deals validated in {elapsed:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
