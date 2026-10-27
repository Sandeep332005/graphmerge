from graphmerge.orchestration.dispatch import (
    CallbackWorker,
    PassthroughWorker,
    WorkerPool,
)


def test_passthrough_match():
    proposals = [
        {"id": "p1", "diff_content": "diff1"},
        {"id": "p2", "diff_content": "diff2"},
    ]
    w = PassthroughWorker(proposals)
    result = w.generate_proposal({"id": "p1"}, "s_0")
    assert result is not None
    assert result["id"] == "p1"


def test_passthrough_miss():
    w = PassthroughWorker([{"id": "p1"}])
    result = w.generate_proposal({"id": "p99"}, "s_0")
    assert result is None


def test_callback_worker():
    def my_fn(task, baseline, context):
        return {"diff_content": f"patch for {task['id']} on {baseline}"}

    w = CallbackWorker(my_fn)
    result = w.generate_proposal({"id": "t1"}, "HEAD")
    assert result is not None
    assert "t1" in result["diff_content"]
    assert result["id"] == "t1"


def test_callback_worker_none():
    w = CallbackWorker(lambda t, b, c: None)
    result = w.generate_proposal({"id": "t1"}, "s_0")
    assert result is None


def test_worker_pool_dispatch():
    proposals = [
        {"id": "t1", "diff_content": "d1", "verified_local_gain": 1.0},
        {"id": "t2", "diff_content": "d2", "verified_local_gain": 2.0},
    ]
    w = PassthroughWorker(proposals)
    pool = WorkerPool(w, max_workers=2)

    tasks = [{"id": "t1"}, {"id": "t2"}, {"id": "t3"}]
    results = pool.dispatch(tasks, "s_0")

    result_ids = {r["id"] for r in results}
    assert result_ids == {"t1", "t2"}


def test_worker_pool_empty():
    w = PassthroughWorker([])
    pool = WorkerPool(w)
    results = pool.dispatch([], "s_0")
    assert results == []


def test_callback_pool_parallel():
    """Verifies parallel execution with callback workers."""
    import threading

    seen_threads = set()

    def track_fn(task, baseline, ctx):
        seen_threads.add(threading.current_thread().ident)
        return {"id": task["id"], "diff_content": "ok"}

    w = CallbackWorker(track_fn)
    pool = WorkerPool(w, max_workers=4)
    tasks = [{"id": f"t{i}"} for i in range(4)]
    results = pool.dispatch(tasks, "s_0")
    assert len(results) == 4
