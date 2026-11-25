from src.detection.debounce import DebounceAlertManager
from src.detection.water_level import NORMAL, SIAGA, WASPADA


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def make(duration=5):
    clock = FakeClock()
    return DebounceAlertManager(duration_sec=duration, clock=clock), clock


def test_starts_normal():
    deb, _ = make()
    assert deb.update(NORMAL) == (NORMAL, False)


def test_change_is_confirmed_only_after_duration():
    deb, clock = make(5)
    assert deb.update(WASPADA) == (NORMAL, False)
    clock.t = 4.9
    assert deb.update(WASPADA) == (NORMAL, False)
    clock.t = 5.0
    assert deb.update(WASPADA) == (WASPADA, True)
    clock.t = 6.0
    assert deb.update(WASPADA) == (WASPADA, False)   # tidak dilaporkan berubah dua kali


def test_flicker_restarts_timer():
    deb, clock = make(5)
    deb.update(SIAGA)
    clock.t = 3
    deb.update(NORMAL)        # kedipan kembali ke normal
    clock.t = 4
    deb.update(SIAGA)
    clock.t = 8.9
    assert deb.update(SIAGA) == (NORMAL, False)
    clock.t = 9
    assert deb.update(SIAGA) == (SIAGA, True)


def test_returns_to_normal_after_duration():
    deb, clock = make(2)
    deb.update(SIAGA)
    clock.t = 2
    deb.update(SIAGA)
    deb.update(NORMAL)
    clock.t = 4
    assert deb.update(NORMAL) == (NORMAL, True)


def test_reset():
    deb, clock = make(1)
    deb.update(SIAGA)
    clock.t = 1
    deb.update(SIAGA)
    deb.reset()
    assert deb.update(NORMAL) == (NORMAL, False)
