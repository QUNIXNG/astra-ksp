"""set_paused: the two pause paths fail in opposite states, so neither alone can resume the other's pause.

Live evidence: pausing through the bridge leaves no pause menu, and kRPC's resume path is ``PauseMenu.Close()``,
which threw ``NullReferenceException`` against that state — a resume that reported failure while the game sat
paused. A menu pause has the mirror-image problem: ``FlightDriver.SetPause(false)`` does not close it.
"""

import threading
import time
import types

import pytest

from astra.errors import AstraError, BridgeError
from astra.ksp import KSP


class FakeKrpc:
    """kRPC's ``paused``: a settable property that closes/opens KSP's pause menu."""

    def __init__(self, state: dict, raises: bool = False):
        self._state = state  # shared with the bridge: both read the same game
        self.raises = raises
        self.sets = []

    def get_status(self):  # the KSP class health-checks the link through this
        return types.SimpleNamespace()

    @property
    def paused(self) -> bool:
        return bool(self._state["paused"])

    @paused.setter
    def paused(self, value: bool) -> None:
        self.sets.append(bool(value))
        if self.raises:
            raise RuntimeError("NullReferenceException: Object reference not set to an instance of an object")
        self._state["paused"] = bool(value)


class FakeBridge:
    def __init__(self, state: dict, reachable: bool = True, takes: bool = True):
        self.state, self.reachable, self.takes = state, reachable, takes
        self.posts = []

    def up(self) -> bool:
        return self.reachable

    def get(self, path, timeout=5.0):
        if not self.reachable:
            raise BridgeError("down")
        return {"paused": bool(self.state["paused"])}

    def post(self, path, payload, timeout=10.0):
        if not self.reachable:
            raise BridgeError("down")
        self.posts.append(dict(payload))
        if self.takes:
            self.state["paused"] = bool(payload["paused"])
        return {"paused": bool(self.state["paused"])}


def make_ksp(*, paused: bool, krpc_raises: bool = False, bridge_reachable: bool = True,
             bridge_takes: bool = True) -> KSP:
    k = KSP.__new__(KSP)  # no connection: the pause logic is the only thing under test here
    k._lock = threading.RLock()
    state = {"paused": paused}
    k._conn = types.SimpleNamespace(krpc=FakeKrpc(state, raises=krpc_raises))
    k._last_health = time.monotonic()
    k.bridge = FakeBridge(state, reachable=bridge_reachable, takes=bridge_takes)
    k.scene = lambda: "flight"  # type: ignore[method-assign]
    return k


def test_a_silent_pause_is_resumed_through_the_bridge_even_if_krpc_would_throw():
    k = make_ksp(paused=True, krpc_raises=True)
    k.set_paused(False, style="silent")
    assert k.paused is False
    assert k.bridge.posts == [{"paused": False}]
    assert k.conn.krpc.sets == []  # never asked the pause menu to close something it did not open


def test_a_menu_pause_is_resumed_even_if_the_bridge_cannot_clear_it():
    k = make_ksp(paused=True, bridge_takes=False)
    k.set_paused(False, style="menu")
    assert k.paused is False
    assert k.conn.krpc.sets == [False]


def test_krpc_that_throws_falls_through_to_the_bridge():
    k = make_ksp(paused=True, krpc_raises=True)
    k.set_paused(False, style="menu")  # menu first: it throws, the bridge finishes the job
    assert k.paused is False


def test_both_paths_failing_says_so_instead_of_claiming_success():
    k = make_ksp(paused=True, krpc_raises=True, bridge_takes=False)
    with pytest.raises(AstraError) as exc:
        k.set_paused(False, style="silent")
    assert "could not set paused=False" in exc.value.message
    assert "pauseMenuOpen" in exc.value.hint


def test_already_in_the_asked_state_costs_nothing():
    k = make_ksp(paused=False, krpc_raises=True)
    k.set_paused(False)
    assert k.bridge.posts == [] and k.conn.krpc.sets == []
