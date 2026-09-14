#!/usr/bin/env python3
"""Scaffold for RQ1 Flannery frequency research.

This file intentionally does not run the experiment yet. Fill in the frozen
Flannery definition and ordinary 1H baseline in config.json before enabling the
classification logic.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flannery_research_harness.validate_harness import generate_deals, pbn_to_cards

CONFIG_PATH = Path(__file__).with_name("config.json")
SUMMARY_PATH = Path(__file__).with_name("summary.json")


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_ready(config: dict[str, Any]) -> None:
    missing = []
    if not config.get("sample_size"):
        missing.append("sample_size")
    if config.get("flannery_definition", {}).get("status") == "placeholder":
        missing.append("flannery_definition")
    if config.get("ordinary_one_heart_baseline", {}).get("status") == "placeholder":
        missing.append("ordinary_one_heart_baseline")
    if config.get("confidence_interval", {}).get("method") == "placeholder":
        missing.append("confidence_interval.method")
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(f"RQ1 is not ready to run; freeze these fields first: {joined}")


def classify_hand(_hand_cards: list[list[int]], _config: dict[str, Any]) -> dict[str, Any]:
    """Return Flannery and baseline classifications for one hand.

    To be implemented once the definition is frozen. The input is one hand in
    the same suit-mask representation used by the validated DDS harness.
    """
    raise NotImplementedError("Hand classification rules are not frozen yet")


def run(config: dict[str, Any]) -> dict[str, Any]:
    ensure_ready(config)
    deals = generate_deals(config["sample_size"], config["seed"])

    # Later implementation: classify all four hands in each generated deal,
    # aggregate frequency, shape mix, strength mix, and 1H-removal rates.
    for pbn in deals:
        _hands = pbn_to_cards(pbn)
        raise NotImplementedError("RQ1 aggregation is not implemented yet")

    return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    args = parser.parse_args()

    config = load_config(args.config)
    summary = run(config)
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
