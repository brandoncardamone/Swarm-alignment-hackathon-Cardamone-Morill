"""Grouping maps. Each map takes a merged stream (list of visible event dicts in stream order)
and returns, for request i, the indices of the requests J judges together with it.
Every group contains i, uses only requests at positions <= i, and is cut to the most recent M."""
from .base import cut
from .clustering import Clustering
from .oracle import Oracle
from .per_agent import PerAgent
from .provenance import Provenance
from .random_matched import RandomMatched
from .singleton import Singleton

__all__ = ["Clustering", "Oracle", "PerAgent", "Provenance", "RandomMatched", "Singleton", "cut"]
