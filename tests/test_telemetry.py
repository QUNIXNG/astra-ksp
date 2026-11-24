"""The slow-metric cache must hand back the caller's failure default.

Regression guard: `read_extended` unpacks two values out of `_slow`. When an RPC failed the helper
used to return a bare `_NAN`, so the unpack raised `TypeError: cannot unpack non-iterable float
object` and took the whole telemetry layer, and every reflex running on it, down with it. One
transient failure (a tracking station without maneuver nodes, a race during staging) was enough.
"""

import math

import pytest

from astra import telemetry
from astra.telemetry import Probe


def _boom():
    raise RuntimeError("Maneuver node editing is not available.")


@pytest.fixture
def probe():
    # `_slow` never touches the connection, so a bare object stands in for the KSP wrapper.
    return Probe(k=object())


def test_a_failed_two_value_read_still_unpacks(probe):
    got = probe._slow("node", 0.5, _boom, (telemetry._NAN, telemetry._NAN))
    a, b = got  # this unpack is the regression: it used to raise TypeError
    assert math.isnan(a) and math.isnan(b)


def test_a_failed_single_value_read_is_nan(probe):
    assert math.isnan(probe._slow("ec", 0.5, _boom))


def test_the_failure_default_is_cached_not_retried(probe):
    calls = []

    def counting():
        calls.append(1)
        raise RuntimeError("boom")

    first = probe._slow("node", 60.0, counting, (telemetry._NAN, telemetry._NAN))
    second = probe._slow("node", 60.0, counting, (telemetry._NAN, telemetry._NAN))
    assert len(calls) == 1
    assert first is second
