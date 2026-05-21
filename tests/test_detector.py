import time

from src.detector import DetectorWorker, stats_indicate_default, stats_indicate_media


class FakeMonitor:
    def __init__(self, frames):
        self.frames = list(frames)
        self.closed = False

    def is_media_displayed(self):
        if len(self.frames) > 1:
            return self.frames.pop(0), None
        return self.frames[0], None

    def close(self):
        self.closed = True


class FakeOBS:
    def __init__(self):
        self.connected = True
        self.switches = []
        self.reverts = 0
        self.disconnected = False

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.disconnected = True
        self.connected = False

    def is_connected(self):
        return self.connected

    def switch_to_media_scene(self, scene):
        self.switches.append(scene)

    def revert_scene(self):
        self.reverts += 1


class DisconnectedOBS(FakeOBS):
    def __init__(self):
        super().__init__()
        self.connected = False
        self.connect_calls = 0

    def connect(self):
        self.connect_calls += 1
        self.connected = True


class FailingSwitchOBS(FakeOBS):
    def __init__(self):
        super().__init__()
        self.disconnects = 0
        self.connect_calls = 0

    def switch_to_media_scene(self, scene):
        raise RuntimeError("switch failed")

    def disconnect(self):
        self.disconnects += 1
        self.connected = False

    def connect(self):
        self.connect_calls += 1
        self.connected = True


def test_stats_indicate_media_uses_threshold_before_baseline():
    assert stats_indicate_media(rms=16, threshold=15) is True
    assert stats_indicate_media(rms=14, threshold=15) is False


def test_stats_indicate_media_uses_baseline_delta():
    assert stats_indicate_media(
        rms=13,
        threshold=15,
        baseline_set=True,
        baseline_rms=5,
        baseline_rms_delta=7,
    ) is True


def test_stats_indicate_default_matches_baseline_band():
    assert stats_indicate_default(
        rms=7,
        baseline_set=True,
        baseline_rms=5,
        mean=11,
        baseline_mean=10,
        bright_frac=0.03,
        baseline_bright=0.02,
    ) is True


def test_stats_indicate_media_uses_mean_and_bright_fraction():
    assert stats_indicate_media(
        rms=2,
        threshold=15,
        baseline_set=True,
        mean=30,
        baseline_mean=10,
    ) is True
    assert stats_indicate_media(
        rms=2,
        threshold=15,
        baseline_set=True,
        bright_frac=0.2,
        baseline_bright=0.1,
    ) is True


def test_stats_indicate_default_rejects_without_baseline_or_mean():
    assert stats_indicate_default(rms=1, baseline_set=False, mean=1) is False
    assert stats_indicate_default(rms=1, baseline_set=True, mean=None) is False


def test_worker_switches_and_reverts_after_required_frames():
    monitor = FakeMonitor([20, 20, 0, 0])
    obs = FakeOBS()
    updates = []
    worker = DetectorWorker(
        monitor_obj=monitor,
        media_scene="Media",
        threshold=15,
        presence_req=2,
        absence_req=2,
        poll_interval=0.001,
        obs_controller=obs,
        update_cb=updates.append,
    )

    worker.start()
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and obs.reverts == 0:
        time.sleep(0.01)
    worker.stop()
    worker.join(timeout=1)

    assert obs.switches == ["Media"]
    assert obs.reverts == 1
    assert monitor.closed is True
    assert obs.disconnected is False
    assert any(update.get("status") == "Switched to Media" for update in updates)
    assert any(update.get("status") == "Reverted scene" for update in updates)


def test_worker_connects_disconnected_injected_obs():
    monitor = FakeMonitor([0])
    obs = DisconnectedOBS()
    worker = DetectorWorker(
        monitor_obj=monitor,
        media_scene="Media",
        threshold=15,
        presence_req=2,
        absence_req=2,
        poll_interval=0.001,
        obs_controller=obs,
    )

    worker.start()
    time.sleep(0.02)
    worker.stop()
    worker.join(timeout=1)

    assert obs.connect_calls == 1


def test_worker_attempts_reconnect_when_switch_fails(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _: None)
    monitor = FakeMonitor([20, 20])
    obs = FailingSwitchOBS()
    worker = DetectorWorker(
        monitor_obj=monitor,
        media_scene="Media",
        threshold=15,
        presence_req=1,
        absence_req=2,
        poll_interval=0.001,
        obs_controller=obs,
    )

    worker.start()
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and obs.connect_calls == 0:
        time.sleep(0)
    worker.stop()
    worker.join(timeout=1)

    assert obs.disconnects >= 1
    assert obs.connect_calls >= 1
