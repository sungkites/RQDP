"""Exhaustive small-instance audit of RBG cost and answer certification."""

from __future__ import annotations

import itertools
import random

from residual_bound_greedy import ResidualBoundGreedy


def main():
    omega = ((0, 0), (0, 1), (1, 0), (1, 1))
    rng = random.Random(290926)
    checked_models = 0
    checked_states = 0
    for _ in range(100):
        n = rng.choice((3, 4))
        radius = rng.choice((0, 1))
        domains = [tuple(sorted(rng.sample(range(4), rng.randint(1, 3)))) for _ in range(n)]
        costs = [rng.randint(1, 4) for _ in range(n)]
        thresholds = [rng.randint(1, n) for _ in range(2)]
        engine = ResidualBoundGreedy(domains, costs, omega, thresholds, radius)
        predicted_worst = engine.worst_cost(engine.start)
        measured_worst = 0
        for truth in itertools.product(range(4), repeat=n):
            if sum(value not in domain for value, domain in zip(truth, domains)) > radius:
                continue
            trace = engine.reference_path(truth)
            assert trace["status"] == "certified"
            target = tuple(int(sum(omega[value][j] for value in truth) >= thresholds[j]) for j in range(2))
            assert trace["answer"] == target
            measured_worst = max(measured_worst, trace["reference_cost"])
            checked_states += 1
        assert measured_worst == predicted_worst
        checked_models += 1
    print({"models": checked_models, "admissible_reference_states": checked_states,
           "wrong_certifications": 0, "worst_cost_mismatches": 0})


if __name__ == "__main__":
    main()
