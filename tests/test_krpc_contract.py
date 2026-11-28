"""Contract with the installed kRPC client.

The ops and reflex tests drive fakes, and a fake cannot notice that kRPC 0.5.4 -> 0.8.0 deleted
``Parts.in_stage`` or ``AutoPilot.engage()``: that is how three ``AttributeError``s reached a live
flight with 532 green tests. These checks read the generated client that will actually be used, so a
kRPC upgrade that drops an API fails here instead of mid-burn.

The client source is generated into ``krpc/ksp/spacecenter.py`` on the first connect; until then the
module does not exist and these checks skip.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from astra import ksp as ksp_mod


def _spacecenter():
    try:
        from krpc.ksp import spacecenter  # noqa: PLC0415 — 生成代码，只在连过一次之后存在
    except ImportError:  # pragma: no cover — 全新 venv 还没连过 kRPC
        pytest.skip("kRPC client not generated yet (connect once)")
    return spacecenter


def test_staging_api_exists():
    """Staging must be reachable: per-stage objects on 0.8.0, `parts.in_stage` before."""
    sc = _spacecenter()
    if hasattr(sc.Vessel, "stage_at"):
        assert hasattr(sc.Vessel, "decouple_stage_at")
        assert hasattr(sc.Stage, "parts")
    else:  # pragma: no cover — 0.5.x
        assert hasattr(sc.Parts, "in_stage") and hasattr(sc.Parts, "in_decouple_stage")


def test_autopilot_has_an_engage_path():
    """`engage()`/`disengage()` are gone in 0.8.0; the writable `engaged` flag replaced them."""
    sc = _spacecenter()
    has_methods = callable(getattr(sc.AutoPilot, "engage", None))
    assert has_methods or hasattr(sc.AutoPilot, "engaged")


def test_closest_approach_api_exists():
    """`distance_at_closest_approach` is gone in 0.8.0: `next_closest_approach(...).distance` replaced it."""
    sc = _spacecenter()
    if hasattr(sc.Orbit, "next_closest_approach"):
        assert hasattr(sc.ClosestApproach, "distance")
    else:  # pragma: no cover — 0.5.x
        assert hasattr(sc.Orbit, "distance_at_closest_approach")


def test_part_tag_still_readable_in_principle():
    """`Part.tag` now carries a ModRequirement (KSPCommunityPartModules/kOS); it must still exist, and
    any read has to go through a guard because it raises at runtime when that mod is missing."""
    sc = _spacecenter()
    assert hasattr(sc.Part, "tag")


# -- the helpers must pick the available shape, whichever kRPC version is installed ------------------


def test_stage_parts_uses_stage_at_when_present():
    parts = [object(), object()]
    vessel = SimpleNamespace(stage_at=lambda n: SimpleNamespace(parts=parts),
                            decouple_stage_at=lambda n: SimpleNamespace(parts=parts),
                            parts=SimpleNamespace(in_stage=lambda n: pytest.fail("used the deleted API")))
    assert ksp_mod.stage_parts(vessel, 3) == parts
    assert ksp_mod.decouple_stage_parts(vessel, 3) == parts


def test_stage_parts_falls_back_to_parts_in_stage():
    parts = [object()]
    vessel = SimpleNamespace(parts=SimpleNamespace(in_stage=lambda n: parts,
                                                   in_decouple_stage=lambda n: parts))
    assert ksp_mod.stage_parts(vessel, 3) == parts
    assert ksp_mod.decouple_stage_parts(vessel, 3) == parts


def test_autopilot_helpers_handle_the_engaged_flag():
    ap = SimpleNamespace(engaged=False)
    ksp_mod.autopilot_engage(ap)
    assert ap.engaged is True
    ksp_mod.autopilot_disengage(ap)
    assert ap.engaged is False


def test_closest_approach_uses_whichever_exists():
    legacy = SimpleNamespace(distance_at_closest_approach=lambda t: 1234.0)
    assert ksp_mod.closest_approach(legacy, object()) == 1234.0
    modern = SimpleNamespace(next_closest_approach=lambda t: SimpleNamespace(distance=5678.0))
    assert ksp_mod.closest_approach(modern, object()) == 5678.0
