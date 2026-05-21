from types import SimpleNamespace

import flet as ft
from PIL import Image

import src.ui.app as app_module
from src.ui.app import App


class FakePage:
    def __init__(self, width=1000):
        self.window = SimpleNamespace(resizable=False)
        self.width = width
        self.window_width = width
        self.padding = None
        self.title = None
        self.theme_mode = None
        self.controls = []
        self.update_count = 0
        self.bottom_appbar = None
        self.on_resize = None

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self):
        self.update_count += 1


class FakeMonitor:
    instances = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.closed = False
        self.frame = (12.34, Image.new("RGB", (8, 8), color="white"))
        FakeMonitor.instances.append(self)

    def is_media_displayed(self):
        return self.frame

    def close(self):
        self.closed = True


class FakeOBSController:
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.connected = False

    def connect(self):
        self.connected = True

    def is_connected(self):
        return self.connected


class FailingOBSController(FakeOBSController):
    def connect(self):
        raise RuntimeError("no OBS")


class FakeWorker:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.started = False
        self.stopped = False
        self.alive = False
        FakeWorker.instances.append(self)

    def start(self):
        self.started = True
        self.alive = True

    def stop(self):
        self.stopped = True
        self.alive = False

    def join(self, timeout=None):
        self.join_timeout = timeout

    def is_alive(self):
        return self.alive


class FakeThread:
    instances = []

    def __init__(self, target, args=(), daemon=False):
        self.target = target
        self.args = args
        self.daemon = daemon
        self.started = False
        FakeThread.instances.append(self)

    def start(self):
        self.started = True


def make_app(monkeypatch, config=None, width=1000):
    monkeypatch.setattr(app_module, "load_obs_config", lambda: config)
    page = FakePage(width=width)
    return App(page), page


def test_app_initializes_page_and_builds_root(monkeypatch):
    app, page = make_app(monkeypatch)

    assert page.title == "JW OBS Monitor"
    assert page.theme_mode == ft.ThemeMode.SYSTEM
    assert page.padding == 20
    assert page.window.resizable is True
    assert page.controls == [app.ui.root]
    assert page.on_resize == app._on_resize


def test_app_loads_saved_config(monkeypatch):
    config = {
        "obs_host": "obs.local",
        "obs_port": "4456",
        "obs_password": "pw",
        "threshold": "22",
        "baseline_rms": 3.5,
        "baseline_rms_delta": "8",
    }

    app, _ = make_app(monkeypatch, config=config)

    assert app.ui.obs_host.value == "obs.local"
    assert app.ui.obs_port.value == "4456"
    assert app.ui.obs_password.value == "pw"
    assert app.ui.threshold.value == "22"
    assert app.ui.baseline_delta.value == "8"
    assert app.baseline_rms == 3.5
    assert app.ui.baseline_rms_text.value == "Baseline RMS: 3.50"


def test_app_resize_keeps_min_width_and_sets_preview_width(monkeypatch):
    app, page = make_app(monkeypatch, width=400)

    app._on_resize(None)

    assert app.ui.main_content.width == app.min_content_width
    assert app.ui.preview_image.width == 160
    assert page.update_count > 0


def test_update_ui_toggles_capture_fields(monkeypatch):
    app, _ = make_app(monkeypatch)

    app.ui.capture_var.value = "window"
    app._update_ui()

    assert app.ui.monitor_idx.disabled is True
    assert app.ui.window_title.disabled is False

    app.ui.capture_var.value = "monitor"
    app._update_ui()

    assert app.ui.monitor_idx.disabled is False
    assert app.ui.window_title.disabled is True


def test_save_obs_config_sends_current_values(monkeypatch, tmp_path):
    app, _ = make_app(monkeypatch)
    saved = {}

    def fake_save(config):
        saved.update(config)
        return tmp_path / "config.json"

    monkeypatch.setattr(app_module, "save_obs_config", fake_save)
    app.ui.obs_host.value = "obs.local"
    app.ui.obs_port.value = "4456"
    app.ui.obs_password.value = "pw"
    app.ui.threshold.value = "21"
    app.ui.baseline_delta.value = "9"
    app.baseline_rms = 4.25

    app._save_obs_config(None)

    assert saved == {
        "obs_host": "obs.local",
        "obs_port": "4456",
        "obs_password": "pw",
        "threshold": "21",
        "baseline_rms": 4.25,
        "baseline_rms_delta": "9",
    }


def test_create_monitor_uses_monitor_mode(monkeypatch):
    app, _ = make_app(monkeypatch)
    FakeMonitor.instances.clear()
    monkeypatch.setattr(app_module, "ScreenMonitor", FakeMonitor)

    monitor = app._create_monitor()

    assert monitor is FakeMonitor.instances[-1]
    assert monitor.kwargs == {"monitor_index": 2, "scale": 0.25}


def test_create_monitor_uses_window_mode(monkeypatch):
    app, _ = make_app(monkeypatch)
    FakeMonitor.instances.clear()
    monkeypatch.setattr(app_module, "WindowMonitor", FakeMonitor)
    app.ui.capture_var.value = "window"
    app.ui.window_title.value = "JW Library"
    app.ui.exact_match.value = True

    monitor = app._create_monitor()

    assert monitor is FakeMonitor.instances[-1]
    assert monitor.kwargs == {"window_title": "JW Library", "scale": 0.25, "exact": True}


def test_prepare_preview_monitor_closes_previous_monitor(monkeypatch):
    app, _ = make_app(monkeypatch)
    FakeMonitor.instances.clear()
    monkeypatch.setattr(app_module, "ScreenMonitor", FakeMonitor)

    assert app._prepare_preview_monitor() is True
    first = app.preview_monitor
    assert app._prepare_preview_monitor() is True

    assert first.closed is True
    assert app.preview_monitor is FakeMonitor.instances[-1]


def test_refresh_preview_updates_image_source(monkeypatch):
    app, _ = make_app(monkeypatch)
    app.preview_monitor = FakeMonitor()

    app._refresh_preview()

    assert app.preview_rms == 12.34
    assert app.ui.preview_rms_text.value == "Preview RMS: 12.34"
    assert app.ui.preview_image.visible is True
    assert app.ui.preview_image.src
    assert app.ui.preview_placeholder.visible is False


def test_set_baseline_uses_preview_monitor(monkeypatch):
    app, _ = make_app(monkeypatch)
    app.preview_monitor = FakeMonitor()

    app._set_baseline(None)

    assert app.baseline_rms == 12.34
    assert app.ui.baseline_rms_text.value == "Baseline RMS: 12.34"


def test_connect_obs_success_updates_status(monkeypatch):
    app, _ = make_app(monkeypatch)
    monkeypatch.setattr(app_module, "OBSController", FakeOBSController)

    app._connect_obs(None)

    assert app.obs_controller.is_connected()
    assert app.ui.obs_status_var.value == "OBS connected to localhost:4455"
    assert app.ui.status_var.value == "OBS connected"


def test_connect_obs_failure_updates_status(monkeypatch):
    app, _ = make_app(monkeypatch)
    monkeypatch.setattr(app_module, "OBSController", FailingOBSController)

    app._connect_obs(None)

    assert app.obs_controller is None
    assert app.ui.obs_status_var.value == "OBS disconnected"


def test_connect_obs_rejects_invalid_port(monkeypatch):
    app, _ = make_app(monkeypatch)
    app.ui.obs_port.value = "bad"

    app._connect_obs(None)

    assert app.obs_controller is None
    assert "Invalid OBS port" in app.ui.status_var.value or app.ui.obs_status_var.value == "OBS: disconnected"


def test_refresh_preview_handles_missing_monitor(monkeypatch):
    app, _ = make_app(monkeypatch)

    app._refresh_preview()

    assert app.ui.preview_placeholder.visible is True
    assert app.ui.preview_image.visible is False
    assert app.ui.preview_rms_text.value == "Preview RMS: -"


def test_refresh_preview_handles_monitor_error(monkeypatch):
    app, _ = make_app(monkeypatch)

    class BrokenMonitor:
        def is_media_displayed(self):
            raise RuntimeError("capture failed")

    app.preview_monitor = BrokenMonitor()

    app._refresh_preview()

    assert app.ui.preview_placeholder.visible is True
    assert app.ui.preview_image.visible is False
    assert app.ui.preview_rms_text.value == "Preview RMS: -"


def test_start_rejects_invalid_settings(monkeypatch):
    app, _ = make_app(monkeypatch)
    app.ui.threshold.value = "bad"

    app.start(None)

    assert app.worker is None
    assert app.ui.start_btn.disabled is False


def test_start_rejects_missing_scene(monkeypatch):
    app, _ = make_app(monkeypatch)
    app.ui.scene_name.value = " "

    app.start(None)

    assert app.worker is None
    assert app.ui.start_btn.disabled is False


def test_monitor_worker_state_ignores_old_worker(monkeypatch):
    app, _ = make_app(monkeypatch)
    old_worker = FakeWorker()
    new_worker = FakeWorker()
    app.worker = new_worker

    app._monitor_worker_state(old_worker)

    assert app.worker is new_worker


def test_monitor_worker_state_resets_current_worker(monkeypatch):
    app, _ = make_app(monkeypatch)
    worker = FakeWorker()
    app.worker = worker
    app.ui.start_btn.disabled = True
    app.ui.stop_btn.disabled = False

    app._monitor_worker_state(worker)

    assert app.worker is None
    assert app.ui.start_btn.disabled is False
    assert app.ui.stop_btn.disabled is True


def test_status_update_prefers_present_state(monkeypatch):
    app, _ = make_app(monkeypatch)

    app._status_update({"status": "Switched", "rms": 5.5, "present": True})

    assert app.ui.rms_var.value == "RMS: 5.5"
    assert app.ui.status_var.value == "Media present"


def test_start_creates_worker_and_stop_stops_it(monkeypatch):
    app, _ = make_app(monkeypatch)
    FakeMonitor.instances.clear()
    FakeWorker.instances.clear()
    FakeThread.instances.clear()
    monkeypatch.setattr(app_module, "ScreenMonitor", FakeMonitor)
    monkeypatch.setattr(app_module, "DetectorWorker", FakeWorker)
    monkeypatch.setattr(app_module.threading, "Thread", FakeThread)

    app.start(None)

    worker = FakeWorker.instances[-1]
    assert worker.started is True
    assert app.worker is worker
    assert app.ui.start_btn.disabled is True
    assert app.ui.stop_btn.disabled is False
    assert FakeThread.instances[-1].started is True
    assert worker.kwargs["media_scene"] == "Media"
    assert worker.kwargs["threshold"] == 15.0

    app.preview_monitor = FakeMonitor()
    app.stop(None)

    assert worker.stopped is True
    assert app.worker is None
    assert app.preview_monitor is None
    assert app.ui.start_btn.disabled is False
    assert app.ui.stop_btn.disabled is True
