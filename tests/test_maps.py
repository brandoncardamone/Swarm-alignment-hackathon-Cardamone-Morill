from swarm_oversight.maps import Clustering, Oracle, PerAgent, Provenance, RandomMatched, Singleton


def ev(i, root, r=(), w=()):
    return {"request_id": f"q{i}", "root_id": root, "request_text": f"t{i}", "paths_read": list(r), "paths_written": list(w)}


# A writes x (0); benign B reads y (1); C reads x and writes z (2); D reads z (3)
STREAM = [ev(0, "A", w=["x"]), ev(1, "B", r=["y"]), ev(2, "C", r=["x"], w=["z"]), ev(3, "D", r=["z"])]
HIDDEN = {"q0": {"episode_id": "atk"}, "q1": {"episode_id": "b1"}, "q2": {"episode_id": "atk"}, "q3": {"episode_id": "atk"}}


def test_singleton_and_per_agent():
    assert Singleton(STREAM).group(3) == [3]
    assert PerAgent(STREAM, M=10).group(3) == [3]


def test_provenance_hops():
    assert Provenance(STREAM, M=10, h=1).group(3) == [2, 3]
    assert Provenance(STREAM, M=10, h=2).group(3) == [0, 2, 3]
    assert Provenance(STREAM, M=2, h=2).group(3) == [2, 3]  # cut to M keeps nearest hop


def test_oracle_and_random():
    assert Oracle(STREAM, M=10, hidden=HIDDEN).group(3) == [0, 2, 3]
    prov = Provenance(STREAM, M=10, h=2)
    g = RandomMatched(STREAM, M=10, provenance=prov).group(3)
    assert len(g) == 3 and g[-1] == 3


def test_clustering_multi():
    emb = [[1, 0], [0, 1], [1, 0.05], [0.7, 0.7]]
    c = Clustering(STREAM, M=10, embeddings=emb, tau_route=0.7, tau_multi=0.7)
    assert c.group(2) == [0, 2]
    assert set(c.group(3)) >= {0, 1, 2, 3}
