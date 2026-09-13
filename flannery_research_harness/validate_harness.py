#!/usr/bin/env python3
"""Validate the Flannery research harness against DDS3.

This script is intentionally dependency-light: outside the Python standard
library it imports only the official ``dds3`` package built from the pinned DDS
source tree. It generates reproducible random deals, solves complete double-
dummy tables in batches, checks several invariants, and writes auditable output
files suitable for later Monte Carlo studies.
"""
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
DEFAULT_SEED = 20260913
DEFAULT_COUNT = 1000


def generate_deals(count: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    deck = [(suit_index, rank) for suit_index in range(4) for rank in RANKS]
    deals: list[str] = []
    for _ in range(count):
        cards = deck.copy()
        rng.shuffle(cards)
        hands = [cards[i * 13 : (i + 1) * 13] for i in range(4)]
        deals.append("N:" + " ".join(_hand_to_pbn(hand) for hand in hands))
    return deals


def _hand_to_pbn(hand: Sequence[tuple[int, str]]) -> str:
    holdings: list[list[str]] = [[] for _ in range(4)]
    for suit_index, rank in hand:
        holdings[suit_index].append(rank)
    rank_pos = {rank: i for i, rank in enumerate(RANKS)}
    return ".".join(
        "".join(sorted(holding, key=rank_pos.__getitem__)) for holding in holdings
    )


def pbn_to_cards(pbn: str) -> list[list[int]]:
    prefix, body = pbn.split(":", 1)
    if prefix != "N":
        raise ValueError(f"Expected N-starting PBN, got {prefix!r}")
    hands = body.split()
    if len(hands) != 4:
        raise ValueError(f"Expected four hands, got {len(hands)}")
    cards: list[list[int]] = []
    for hand in hands:
        holdings = hand.split(".")
        if len(holdings) != 4:
            raise ValueError(f"Bad hand: {hand}")
        masks: list[int] = []
        for holding in holdings:
            mask = 0
            for rank in holding:
                mask |= 1 << RANK_VALUE[rank]
            masks.append(mask)
        cards.append(masks)
    return cards


def rotate_clockwise(pbn: str) -> str:
    prefix, body = pbn.split(":", 1)
    if prefix != "N":
        raise ValueError("Rotation helper expects N-starting PBN")
    hands = body.split()
    if len(hands) != 4:
        raise ValueError("Rotation helper expects four hands")
    rotated = [hands[3], hands[0], hands[1], hands[2]]
    return "N:" + " ".join(rotated)


def solve_batches(deals: Sequence[str], batch_size: int, max_threads: int) -> list[list[list[int]]]:
    tables: list[list[list[int]]] = []
    for start in range(0, len(deals), batch_size):
        chunk = list(deals[start : start + batch_size])
        result = calc_all_tables_pbn(
            chunk,
            mode=-1,
            trump_filter=[0, 0, 0, 0, 0],
            max_threads=max_threads,
        )
        if result["no_of_boards"] != len(chunk):
            raise AssertionError(
                f"DDS returned {result['no_of_boards']} boards for {len(chunk)} inputs"
            )
        if len(result["tables"]) != len(chunk):
            raise AssertionError("DDS table count does not match input count")
        tables.extend(table["res_table"] for table in result["tables"])
    return tables


def validate_table_shape_and_range(tables: Sequence[Sequence[Sequence[int]]]) -> None:
    for board_index, table in enumerate(tables):
        if len(table) != 5:
            raise AssertionError(f"Board {board_index}: expected 5 strains, got {len(table)}")
        for strain_index, row in enumerate(table):
            if len(row) != 4:
                raise AssertionError(f"Board {board_index}, strain {strain_index}: expected 4 seats")
            for tricks in row:
                if not isinstance(tricks, int) or not 0 <= tricks <= 13:
                    raise AssertionError(f"Board {board_index}: invalid DD trick count {tricks!r}")


def validate_single_batch_parity(deals, batch_tables, n: int) -> None:
    for i in range(min(n, len(deals))):
        single = calc_dd_table({"cards": pbn_to_cards(deals[i])})["res_table"]
        if single != batch_tables[i]:
            raise AssertionError(f"Single/batch mismatch at board {i}")


def validate_thread_determinism(deals, expected, n: int) -> None:
    sample = list(deals[: min(n, len(deals))])
    if not sample:
        return
    one = solve_batches(sample, batch_size=min(50, len(sample)), max_threads=1)
    four = solve_batches(sample, batch_size=min(50, len(sample)), max_threads=4)
    target = list(expected[: len(sample)])
    if one != target:
        raise AssertionError("One-thread results differ from primary run")
    if four != target:
        raise AssertionError("Four-thread results differ from primary run")


def validate_rotation_symmetry(deals, expected, n: int) -> None:
    sample_count = min(n, len(deals))
    if sample_count == 0:
        return
    rotated_deals = [rotate_clockwise(deals[i]) for i in range(sample_count)]
    rotated_tables = solve_batches(rotated_deals, batch_size=min(50, sample_count), max_threads=2)
    for i, (original, rotated) in enumerate(zip(expected[:sample_count], rotated_tables)):
        for strain in range(5):
            for old_seat in range(4):
                new_seat = (old_seat + 1) % 4
                if original[strain][old_seat] != rotated[strain][new_seat]:
                    raise AssertionError(
                        "Rotation mismatch at board "
                        f"{i}, strain={strain}, old_seat={old_seat}, new_seat={new_seat}"
                    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_outputs(out_dir: Path, deals, tables, metadata: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    deals_text = "\n".join(deals) + "\n"
    (out_dir / "validation_deals.pbn").write_text(deals_text, encoding="utf-8")

    columns = ["board", "pbn"]
    for strain in STRAINS:
        for seat in SEATS:
            columns.append(f"{strain}_{seat}")
    with (out_dir / "validation_tables.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for board_index, (pbn, table) in enumerate(zip(deals, tables)):
            row: dict[str, object] = {"board": board_index, "pbn": pbn}
            for strain_index, strain in enumerate(STRAINS):
                for seat_index, seat in enumerate(SEATS):
                    row[f"{strain}_{seat}"] = table[strain_index][seat_index]
            writer.writerow(row)

    table_payload = json.dumps(tables, separators=(",", ":"), ensure_ascii=True)
    metadata = dict(metadata)
    metadata["deals_sha256"] = sha256_text(deals_text)
    metadata["tables_sha256"] = sha256_text(table_payload)
    metadata["combined_sha256"] = sha256_text(deals_text + "\n" + table_payload)
    (out_dir / "validation_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = [
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
    (out_dir / "VALIDATION_PASS.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.count <= 0:
        parser.error("--count must be positive")
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    if args.threads <= 0:
        parser.error("--threads must be positive")

    started = time.perf_counter()
    deals = generate_deals(args.count, args.seed)
    if deals != generate_deals(args.count, args.seed):
        raise AssertionError("Deal generator is not deterministic")
    if len(set(deals)) != len(deals):
        raise AssertionError("Duplicate deals appeared in validation sample")

    tables = solve_batches(deals, args.batch_size, args.threads)
    validate_table_shape_and_range(tables)
    validate_single_batch_parity(deals, tables, n=10)
    validate_thread_determinism(deals, tables, n=50)
    validate_rotation_symmetry(deals, tables, n=25)

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
