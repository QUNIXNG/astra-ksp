"""execute_node must time the burn against the node that is in front of it, not the one it read before the coast.

Live evidence: a node was placed 3,793 s in the future, the coast ran, and KSP had replaced the node (a node whose
orbit changes is re-created, not kept). Timing the old UT reported "-3793.2 s relative to the planned start" — a
number that reads like a piloting failure while the real state was "this is not the node that was planned".
"""


from astra.reflex.burn import rebase_start


def test_a_node_that_stayed_put_is_flown_on_the_original_schedule():
    out = rebase_start(planned_node_ut=2000.0, node_ut_now=2000.0, lead_s=10.0, now_ut=1000.0, max_late_s=5.0)
    assert out["start_ut"] == 1990.0
    assert out["note"] is None and out["give_up"] is None
    assert out["moved_s"] == 0.0


def test_a_node_that_moved_is_flown_at_its_new_time_and_named():
    out = rebase_start(planned_node_ut=2000.0, node_ut_now=6000.0, lead_s=10.0, now_ut=1000.0, max_late_s=5.0)
    assert out["start_ut"] == 5990.0  # the new node's schedule, not the old one's
    assert out["moved_s"] == 4000.0
    assert "the node moved +4000.0 s" in out["note"]
    assert out["give_up"] is None


def test_a_window_that_has_already_closed_gives_up_instead_of_chasing_it():
    # The live case: prepared against a node 3,793 s ahead, arrived with the window long past.
    out = rebase_start(planned_node_ut=1000.0, node_ut_now=1000.0, lead_s=10.0, now_ut=4793.2, max_late_s=5.0)
    assert out["start_ut"] == 990.0
    assert "already 3803.2 s past" in out["give_up"]
    assert "node_set" in out["give_up"]


def test_moving_and_already_late_reports_both():
    out = rebase_start(planned_node_ut=1000.0, node_ut_now=1200.0, lead_s=10.0, now_ut=1500.0, max_late_s=5.0)
    assert out["note"] is not None and out["give_up"] is not None
