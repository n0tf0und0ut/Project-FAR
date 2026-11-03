#!/usr/bin/env python3
"""Replay MAS-MATCHED-002 using the exact recorded single-thread CPU runtime.

Post-execution verifier repair: the preregistered runner source remains unchanged.
The original failed unpinned replay is preserved as negative evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
import model_architecture_replication as replication


def verify_with_recorded_threads(report, journal):
    threads = report.get("environment", {}).get("threads")
    if type(threads) is not int or threads != 1:
        raise ValueError("v0.2 recorded environment must bind CPU thread count to 1")
    if report.get("protocol", {}).get("device") != "cpu":
        raise ValueError("unsupported device for exact replay")
    torch.set_num_threads(threads)
    if torch.get_num_threads() != threads:
        raise RuntimeError("could not restore CPU thread count")
    replication.validate_report(report, journal, replay=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    verify_with_recorded_threads(report, args.journal.read_bytes())
    print("exact training and model-state replay PASS:", report["study_id"], len(report["records"]), "runs")


if __name__ == "__main__":
    main()
