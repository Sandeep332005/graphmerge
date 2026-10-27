from graphmerge.orchestration.sandbox import sandbox_integration_node_real


def test_stub_fallback_no_workspace():
    """Without workspace_path, falls back to stub baseline bumping."""
    state = {
        "newly_accepted": [{"id": "p1", "diff_content": "d"}],
        "accepted_patches": [],
        "staged_patches": [],
        "iteration": 0,
        "max_iterations": 3,
    }
    result = sandbox_integration_node_real(state)
    assert result["current_baseline"] == "s_1"
    assert result["iteration"] == 1
    assert len(result["accepted_patches"]) == 1
    assert result["is_converged"] is True


def test_stub_fallback_with_staged():
    """Staged patches + iteration < max → not converged."""
    state = {
        "newly_accepted": [{"id": "p1"}],
        "accepted_patches": [],
        "staged_patches": [{"id": "p2"}],
        "iteration": 0,
        "max_iterations": 3,
    }
    result = sandbox_integration_node_real(state)
    assert result["is_converged"] is False
    assert result["iteration"] == 1


def test_stub_converges_at_max_iter():
    """Even with staged patches, converges at max_iterations."""
    state = {
        "newly_accepted": [{"id": "p1"}],
        "accepted_patches": [],
        "staged_patches": [{"id": "p2"}],
        "iteration": 2,
        "max_iterations": 3,
    }
    result = sandbox_integration_node_real(state)
    assert result["is_converged"] is True
    assert result["iteration"] == 3


def test_empty_newly_accepted():
    state = {
        "newly_accepted": [],
        "accepted_patches": [{"id": "prev"}],
        "staged_patches": [],
        "iteration": 0,
        "max_iterations": 3,
    }
    result = sandbox_integration_node_real(state)
    assert result["current_baseline"] == "s_1"
    assert len(result["accepted_patches"]) == 1
    assert result["accepted_patches"][0]["id"] == "prev"


def test_accumulates_accepted():
    """Newly accepted patches accumulate with existing accepted."""
    state = {
        "newly_accepted": [{"id": "p2"}],
        "accepted_patches": [{"id": "p1"}],
        "staged_patches": [],
        "iteration": 1,
        "max_iterations": 5,
    }
    result = sandbox_integration_node_real(state)
    ids = [p["id"] for p in result["accepted_patches"]]
    assert ids == ["p1", "p2"]


def test_nonexistent_workspace_falls_back():
    """Workspace path that isn't a git repo falls back to stub."""
    state = {
        "newly_accepted": [{"id": "p1"}],
        "accepted_patches": [],
        "staged_patches": [],
        "workspace_path": "/nonexistent/path",
        "iteration": 0,
        "max_iterations": 3,
    }
    result = sandbox_integration_node_real(state)
    assert result["current_baseline"] == "s_1"
