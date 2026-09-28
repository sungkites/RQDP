"""Lexicographic RQDP for exact cost and earlier query certification.

The primary objective is unchanged: minimise the worst-case verification cost.
Among policies with the same primary value, the second objective minimises the
worst-case area under the number of unresolved queries.  The secondary term is
probability-free and therefore does not introduce calibrated outcome weights.
"""

from dominance import Dominance


class AnytimeDominance(Dominance):
    """RQDP with a cost-preserving anytime tie-break."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Kernel cached the overridden method during construction.  Replace it
        # with a cache around this class' implementation.
        from functools import lru_cache

        self.value = lru_cache(None)(self._value_anytime)

    def _value_anytime(self, state):
        self.guard()
        if self.certain(state):
            return 0, 0, -1
        self.expanded += 1
        if self.expanded > self.limit:
            raise RuntimeError("state limit")

        ns, z, r = state
        active = tuple(j for j, value in enumerate(z) if value >= 0)
        actions = sorted(
            (t for t, count in enumerate(ns) if count),
            key=lambda t: (self.types[t][1], t),
        )
        full_cost = sum(n * c for n, (_, c) in zip(ns, self.types))
        # Auditing every remaining record is always feasible.  The area upper
        # bound is deliberately loose and is used only before a real candidate
        # is found.
        best = (full_cost, len(active) * full_cost, actions[0])

        for t in actions:
            cost = self.types[t][1]
            next_counts = list(ns)
            next_counts[t] -= 1
            next_counts = tuple(next_counts)
            children = set()
            for projected, delta in self.signature(t, active, r > 0)[1]:
                next_z = list(z)
                for j, value in zip(active, projected):
                    next_z[j] = min(self.k[j], next_z[j] + value)
                children.add(self.normalize((next_counts, tuple(next_z), r - delta)))

            worst_child = (0, 0)
            pruned = False
            for child in sorted(children, key=lambda ch: (self.certain(ch), -ch[2], ch)):
                child_value = self.value(child)[:2]
                if child_value > worst_child:
                    worst_child = child_value
                candidate_prefix = (cost + worst_child[0], cost * len(active) + worst_child[1])
                if candidate_prefix >= best[:2]:
                    pruned = True
                    break
            if not pruned:
                candidate = (
                    cost + worst_child[0],
                    cost * len(active) + worst_child[1],
                    t,
                )
                if candidate < best:
                    best = candidate
        return best

    def plan(self, state):
        canonical = self.normalize(state)
        return self.value(canonical), canonical

