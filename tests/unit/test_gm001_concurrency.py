import threading

from graphmerge.mcp_server import arbitrate_merge_proposals


def test_concurrent_optimizer_isolation():
    results = []

    def call_arb(proposals, delay):
        # Simulate some processing delay if needed, though here we just call it
        res = arbitrate_merge_proposals(proposals)
        results.append(res)

    p1 = [{"id": "a", "files": {"x.py": {"f1"}}, "weight": 1.0}]
    p2 = [{"id": "b", "files": {"y.py": {"f2"}}, "weight": 1.0}]

    t1 = threading.Thread(target=call_arb, args=(p1, 0))
    t2 = threading.Thread(target=call_arb, args=(p2, 0))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(results) == 2
    # Result 1 should only have 'a'
    # Result 2 should only have 'b'
    # If shared optimizer was used, one might have both or one might be empty/wrong
    # We find which result corresponds to which input
    res_a = next(r for r in results if "a" in r["accepted_proposals"])
    res_b = next(r for r in results if "b" in r["accepted_proposals"])

    assert res_a["total_nodes"] == 1
    assert res_b["total_nodes"] == 1
    assert "a" in res_a["accepted_proposals"]
    assert "b" in res_b["accepted_proposals"]
    assert "b" not in res_a["accepted_proposals"]
    assert "a" not in res_b["accepted_proposals"]
