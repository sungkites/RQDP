"""Prepare identifier-free V16 predicate data from fixed public splits.

Hospital and Beers use a deterministic 20% development split.  Candidate
correction patterns are learned only from that split.  Clean evaluation rows
are used only for the reference predicate vector and coverage audit.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
RAW = WORKSPACE / "9数据集部分" / "可信查询冲突治理_V14"
OUT = ROOT / "data"


def norm(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def number(value: str):
    match = re.search(r"[-+]?\d*\.?\d+", norm(value))
    return float(match.group()) if match else None


def stable_int(value: str) -> int:
    return int(hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12], 16)


def load(dataset: str, part: str):
    path = RAW / dataset / f"{part}.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def hospital_vector(row, clean=False):
    emergency = "EmergencyService" if clean else "emergency_service"
    owner = "HospitalOwner" if clean else "owner"
    return (
        int(norm(row[emergency]) == "yes"),
        int("government" in norm(row[owner])),
        int("proprietary" in norm(row[owner])),
    )


def beers_vector(row, clean=False):
    abv = number(row["abv"])
    return (
        int(abv is not None and abv >= 0.055),
        int("ipa" in norm(row["style"])),
        int(norm(row["state"]) in {"ca", "or", "wa", "co"}),
    )


def prepare(dataset, vector_fn, id_field):
    dirty = load(dataset, "dirty")
    clean = load(dataset, "clean")
    if len(dirty) != len(clean):
        raise ValueError(f"unaligned {dataset} rows")

    dev_patterns = Counter()
    evaluation = []
    for dirty_row, clean_row in zip(dirty, clean):
        row_id = dirty_row[id_field]
        dirty_vector = vector_fn(dirty_row, False)
        clean_vector = vector_fn(clean_row, True)
        delta = tuple(a ^ b for a, b in zip(dirty_vector, clean_vector))
        item = (row_id, dirty_vector, clean_vector, delta)
        if stable_int(row_id) % 5 == 0:
            dev_patterns[delta] += 1
        else:
            evaluation.append(item)

    patterns = tuple(sorted(dev_patterns, key=lambda p: (-dev_patterns[p], p)))
    omega = list(itertools.product((0, 1), repeat=3))
    omega_index = {v: i for i, v in enumerate(omega)}
    records = []
    omissions = 0
    unseen = Counter()
    for row_id, dirty_vector, clean_vector, delta in sorted(
        evaluation, key=lambda item: stable_int(item[0])
    ):
        candidates = {
            tuple(value ^ change for value, change in zip(dirty_vector, pattern))
            for pattern in patterns
        }
        domain = sorted(omega_index[v] for v in candidates)
        truth = omega_index[clean_vector]
        if truth not in domain:
            omissions += 1
            unseen[delta] += 1
        records.append(
            {
                "domain": domain,
                "truth": truth,
                "cost_h": 1 + stable_int(f"cost:{row_id}") % 4,
            }
        )

    payload = {
        "omega": [list(v) for v in omega],
        "collections": [{"kind": "evaluation", "records": records}],
        "metadata": {
            "split": "sha256(identifier) modulo 5; residue 0 development, others evaluation",
            "development_rows": sum(dev_patterns.values()),
            "evaluation_rows": len(records),
            "candidate_rule": "dirty predicate vector xor each correction pattern observed in development",
            "development_patterns": [
                {"delta": list(pattern), "count": dev_patterns[pattern]} for pattern in patterns
            ],
            "reference_omissions": omissions,
            "reference_coverage": 1 - omissions / len(records),
            "unseen_patterns": [
                {"delta": list(pattern), "count": count} for pattern, count in unseen.items()
            ],
            "identifiers_released": False,
        },
    }
    (OUT / f"{dataset}_predicates.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return payload["metadata"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {
        "hospital": prepare("hospital", hospital_vector, "index"),
        "beers": prepare("beers", beers_vector, "index"),
    }
    (OUT / "v16_preparation_audit.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

