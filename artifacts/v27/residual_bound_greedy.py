"""Query-bound greedy verification under the same deterministic omission model.

The policy chooses an inspection from the reduction in the number of count
pairs that straddle each unresolved threshold. It uses a worst-feedback score
and a feedback-average tie break. The average is a score over distinct feedback
classes, not an outcome probability. Full feedback is used for actual updates.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = Path(os.environ["RQDP_REPO"]) if os.environ.get("RQDP_REPO") else (
    ROOT if (ROOT / "src" / "workloads.py").exists() else ROOT / "5实验代码" / "可信查询冲突治理_V16"
)
sys.path.insert(0, str(SOURCE / "src"))

from dominance import Dominance  # noqa: E402


class ResidualBoundGreedy(Dominance):
    """Approximate policy with exact answer certification and no world listing."""

    def __init__(self, domains, costs, omega, thresholds, radius):
        super().__init__(domains, costs, omega, thresholds, radius, time_limit=3600)
        self.choices = 0
        self.score_calls = 0
        self.potential = lru_cache(None)(self._potential)
        self.choose = lru_cache(None)(self._choose)
        self.worst_cost = lru_cache(None)(self._worst_cost)

    def _potential(self, state):
        value = 0
        for j, (lower, upper) in enumerate(self.bounds(state)):
            if state[1][j] >= 0 and lower < self.k[j] <= upper:
                value += (self.k[j] - lower) * (upper - self.k[j] + 1)
        return value

    def children(self, state, typ):
        counts, known, radius = state
        active = tuple(j for j, contribution in enumerate(known) if contribution >= 0)
        remainder = list(counts)
        remainder[typ] -= 1
        result = set()
        for projected, delta in self.signature(typ, active, radius > 0)[1]:
            updated = list(known)
            for j, value in zip(active, projected):
                updated[j] = min(self.k[j], updated[j] + value)
            result.add(self.normalize((tuple(remainder), tuple(updated), radius - delta)))
        return tuple(sorted(result))

    def _choose(self, state):
        canonical = self.normalize(state)
        if self.certain(canonical):
            return -1
        self.choices += 1
        before = self.potential(canonical)
        best = None
        selected = None
        for typ, count in enumerate(canonical[0]):
            if not count:
                continue
            self.score_calls += 1
            children = self.children(canonical, typ)
            residual = [self.potential(child) for child in children]
            cost = self.types[typ][1]
            # Maximal residual ambiguity is adversarial. The mean over distinct
            # feedback classes is only a deterministic tie-breaking score.
            score = (
                round((before - max(residual)) / cost, 12),
                round((before - sum(residual) / len(residual)) / cost, 12),
                -cost,
                -typ,
            )
            if best is None or score > best:
                best, selected = score, typ
        return selected

    def _worst_cost(self, state):
        canonical = self.normalize(state)
        if self.certain(canonical):
            return 0
        typ = self.choose(canonical)
        return self.types[typ][1] + max(self.worst_cost(child) for child in self.children(canonical, typ))

    def reference_path(self, truth):
        counts = list(self.start[0])
        known = [0] * self.J
        radius = self.start[2]
        remaining = set(range(len(truth)))
        path = []
        total_cost = 0
        while True:
            state = (tuple(counts), tuple(known), radius)
            answers = tuple(
                1 if lower >= threshold else 0 if upper < threshold else None
                for (lower, upper), threshold in zip(self.bounds(state), self.k)
            )
            path.append((total_cost, answers))
            if all(answer is not None for answer in answers):
                return {"status": "certified", "path": path, "reference_cost": total_cost,
                        "inspections": len(path) - 1, "answer": answers}
            canonical = self.normalize(state)
            typ = self.choose(canonical)
            active = tuple(j for j, contribution in enumerate(canonical[1]) if contribution >= 0)
            signature = self.signature(typ, active, canonical[2] > 0)
            record = min(
                i for i in remaining
                if self.signature(self.record_types[i], active, canonical[2] > 0) == signature
            )
            original_type = self.record_types[record]
            outcome = truth[record]
            extra = int(outcome not in self.types[original_type][0])
            if extra > radius:
                return {"status": "support_violation", "path": path}
            remaining.remove(record)
            counts[original_type] -= 1
            radius -= extra
            total_cost += self.types[original_type][1]
            known = [
                min(threshold, contribution + value)
                for threshold, contribution, value in zip(self.k, known, self.omega[outcome])
            ]
