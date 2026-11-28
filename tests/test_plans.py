"""plans.py: a plan id fingerprints the burn that was chosen, not the Δv KSP currently reports for it.

KSP re-solves a node's Δv from the live orbit, so the same planned burn reads 48.09 m/s when it is placed
and 52.63 m/s an hour later. Comparing magnitudes therefore rejects a node that is still exactly the
planned burn; comparing the unit vector and the time does not.
"""

from types import SimpleNamespace

import pytest

from astra import plans


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(plans, "CONFIG", SimpleNamespace(cache_dir=tmp_path))
    return plans


def test_mismatch_names_the_field_that_drifted(store):
    pid = store.remember("circularize", 1500.0, 100.0, 0.0, 0.0)
    assert store.mismatch(pid, ut=1500.0, prograde=100.0, normal=0.0, radial=0.0) is None
    drift = store.mismatch(pid, ut=1500.0, prograde=52.63, normal=0.0, radial=0.0)
    assert drift is not None and "prograde" in drift


def test_direction_mismatch_accepts_a_node_whose_magnitude_krpc_recomputed(store):
    pid = store.remember("hohmann_to_body", 2858588.0, 52.63, 0.0, 0.0)
    assert store.direction_mismatch(pid, ut=2858588.0, prograde=48.09, normal=0.0, radial=0.0) is None
    assert store.direction_mismatch(pid, ut=2858588.3, prograde=52.63, normal=0.0, radial=0.0) is None


def test_direction_mismatch_rejects_a_different_burn(store):
    pid = store.remember("hohmann_to_body", 2858588.0, 100.0, 0.0, 0.0)
    turned = store.direction_mismatch(pid, ut=2858588.0, prograde=100.0, normal=50.0, radial=0.0)
    assert turned is not None and "away from this burn" in turned
    late = store.direction_mismatch(pid, ut=2859088.0, prograde=100.0, normal=0.0, radial=0.0)
    assert late is not None and "burns at UT" in late


def test_a_plan_that_was_never_stored_is_reported_not_guessed(store):
    assert "not in the local cache" in store.direction_mismatch(
        "deadbeef", ut=1.0, prograde=1.0, normal=0.0, radial=0.0)
    assert "not in the local cache" in store.mismatch(
        "deadbeef", ut=1.0, prograde=1.0, normal=0.0, radial=0.0)
