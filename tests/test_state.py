from core.state import InstallState
from core.progress import ProgressState


def test_install_state_has_progress():
    state = InstallState()

    assert isinstance(state.progress, ProgressState)


def test_install_state_default_values():
    state = InstallState()

    assert state.run_mode == "Демонстрационный"
    assert state.mode == "Единая"
    assert state.iso_path == ""
    assert state.network == {}
    assert state.check_results == []


def test_install_state_instances_are_independent():
    first = InstallState()
    second = InstallState()

    first.network["ip"] = "192.168.1.10"
    first.check_results.append({"name": "test", "ok": True})

    assert second.network == {}
    assert second.check_results == []


def test_public_snapshot_contains_required_fields():
    state = InstallState()
    snapshot = state.public_snapshot()

    assert "version" in snapshot
    assert "current_stage" in snapshot
    assert "progress" in snapshot

    assert "status" in snapshot["progress"]
    assert "elapsed_seconds" in snapshot["progress"]


def test_public_snapshot_does_not_change_original_network():
    state = InstallState()
    state.network = {"ip": "192.168.1.10"}

    snapshot = state.public_snapshot()
    snapshot["network"]["ip"] = "10.0.0.1"

    assert state.network["ip"] == "192.168.1.10"