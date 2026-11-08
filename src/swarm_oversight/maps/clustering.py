import numpy as np

from .base import cut


class Clustering:
    """Provider-side map, Brown-style (Brown et al. 2026, Alg. 1, from the paper's description):
    each request is embedded and routed online to centroids by dot product (unit-normalised).
    If no centroid has similarity >= tau_route, a new cluster opens; otherwise the matching centroid
    is updated as a running mean. Multi-cluster assignment: the request joins every cluster with
    similarity >= tau_multi (their red-team fix). The group is the union of those clusters' earlier
    members, cut to the most recent M. Only request text is embedded (a provider sees no paths)."""
    name = "clustering"

    def __init__(self, stream, M: int, embeddings, tau_route: float = 0.80, tau_multi: float | None = None):
        self.M = M
        tau_multi = tau_route if tau_multi is None else tau_multi
        X = np.asarray(embeddings, dtype=np.float32)
        X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
        cents, counts, members = [], [], []
        self.groups_of = []
        for i, x in enumerate(X):
            if cents:
                C = np.stack(cents)
                C = C / (np.linalg.norm(C, axis=1, keepdims=True) + 1e-9)
                sims = C @ x
                best = int(sims.argmax())
            if not cents or sims[best] < tau_route:
                cents.append(x.copy()); counts.append(1); members.append([i])
                self.groups_of.append([len(cents) - 1])
                continue
            assigned = sorted(set([best] + [int(c) for c in np.where(sims >= tau_multi)[0]]))
            for c in assigned:
                counts[c] += 1
                cents[c] += (x - cents[c]) / counts[c]
                members[c].append(i)
            self.groups_of.append(assigned)
        self.members = members

    def group(self, i: int) -> list[int]:
        idx = set()
        for c in self.groups_of[i]:
            idx.update(j for j in self.members[c] if j < i)
        return cut(idx, i, self.M)
