"""Ideal opaque cells: 2 mixes x 2 users, 16-tick cyclic calendar, four epochs, capacity2, gap4/quota1, 512-byte cells. Independent train/validation/test episodes (seeds11/17/29) fit a held-out attacker for each registered defense."""

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def build_steps(args):
    output = (ROOT / args.output).resolve()
    return [
        ["-m", "cascadebalance", "prepare", "--count", "400", "--seed", "11", "--output", str(output / "train.jsonl")],
        ["-m", "cascadebalance", "suite", "--data", str(output / "train.jsonl"), "--methods", "sparse_public", "dense_public", "no_defense", "--output", str(output / "train")],
        ["-m", "cascadebalance", "prepare", "--count", "200", "--seed", "17", "--output", str(output / "validation.jsonl")],
        ["-m", "cascadebalance", "suite", "--data", str(output / "validation.jsonl"), "--methods", "sparse_public", "dense_public", "no_defense", "--output", str(output / "validation")],
        ["-m", "cascadebalance", "prepare", "--count", "200", "--seed", "29", "--output", str(output / "test.jsonl")],
        ["-m", "cascadebalance", "suite", "--data", str(output / "test.jsonl"), "--methods", "sparse_public", "dense_public", "no_defense", "--output", str(output / "test")],
        ["-m", "cascadebalance.attack", "--train", str(output / "train/sparse_public/records.jsonl"), "--validation", str(output / "validation/sparse_public/records.jsonl"), "--test", str(output / "test/sparse_public/records.jsonl"), "--seed", "17", "--fpr", "0.01", "--output", str(output / "attacker_sparse_public")],
        ["-m", "cascadebalance.attack", "--train", str(output / "train/dense_public/records.jsonl"), "--validation", str(output / "validation/dense_public/records.jsonl"), "--test", str(output / "test/dense_public/records.jsonl"), "--seed", "17", "--fpr", "0.01", "--output", str(output / "attacker_dense_public")],
        ["-m", "cascadebalance.attack", "--train", str(output / "train/no_defense/records.jsonl"), "--validation", str(output / "validation/no_defense/records.jsonl"), "--test", str(output / "test/no_defense/records.jsonl"), "--seed", "17", "--fpr", "0.01", "--output", str(output / "attacker_no_defense")],
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default='runs/fixed-setting')
    parser.add_argument("--plan", action="store_true", help="Print commands without creating data, fitting, inference or evaluation")

    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if not args.plan and output.exists():
        parser.error("Choose a fresh --output directory")
    for step in build_steps(args):
        command = [sys.executable, *step]
        if args.plan:
            print(json.dumps(command))
        else:
            subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
