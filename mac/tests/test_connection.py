from stick.connection import ConnectionMonitor


def make(results):
    changes = []
    it = iter(results)
    monitor = ConnectionMonitor(lambda: next(it), changes.append, 1.0, 10.0)
    return monitor, changes


def test_first_check_reports_state_even_when_offline():
    monitor, changes = make([False])
    assert monitor.step() == 1.0
    assert changes == [False]


def test_reports_only_when_state_flips():
    monitor, changes = make([False, False, True, True, False])
    waits = [monitor.step() for _ in range(5)]
    assert changes == [False, True, False]
    assert waits == [1.0, 1.0, 10.0, 10.0, 1.0]  # slow down when online, speed up when offline


def test_a_failing_check_counts_as_offline():
    changes = []

    def boom():
        raise RuntimeError("x")

    monitor = ConnectionMonitor(boom, changes.append, 1.0, 10.0)
    assert monitor.step() == 1.0
    assert changes == [False]
