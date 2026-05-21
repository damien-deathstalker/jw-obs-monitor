from types import SimpleNamespace

import pytest
from PIL import Image

import src.screen_monitor as screen_monitor
from src.screen_monitor import ScreenMonitor, WindowMonitor


class FakeShot:
    def __init__(self, width=4, height=2, rgb=None):
        self.width = width
        self.height = height
        self.size = (width, height)
        self.rgb = rgb or bytes([0, 0, 0, 255, 255, 255] * (width * height // 2))


class FakeMSS:
    instances = []

    def __init__(self):
        self.monitors = [
            {"left": 0, "top": 0, "width": 10, "height": 10},
            {"left": 0, "top": 0, "width": 4, "height": 2},
            {"left": 4, "top": 0, "width": 4, "height": 2},
        ]
        self.grab_calls = []
        self.closed = False
        FakeMSS.instances.append(self)

    def grab(self, bbox):
        self.grab_calls.append(bbox)
        width = bbox.get("width", 4)
        height = bbox.get("height", 2)
        return FakeShot(width=width, height=height)

    def close(self):
        self.closed = True


class FakeWin32Gui:
    def __init__(self, titles=None, client_fails=False, rect=(10, 20, 50, 60)):
        self.titles = titles or {1: "JW Library", 2: "Other"}
        self.client_fails = client_fails
        self.rect = rect

    def EnumWindows(self, callback, extra):
        for hwnd in self.titles:
            should_continue = callback(hwnd, extra)
            if should_continue is False:
                break

    def IsWindowVisible(self, hwnd):
        return True

    def IsIconic(self, hwnd):
        return False

    def GetWindowText(self, hwnd):
        return self.titles.get(hwnd, "")

    def GetClientRect(self, hwnd):
        if self.client_fails:
            raise RuntimeError("client fail")
        return (0, 0, 40, 30)

    def ClientToScreen(self, hwnd, point):
        x, y = point
        return x + 10, y + 20

    def GetWindowRect(self, hwnd):
        return self.rect


@pytest.fixture(autouse=True)
def fake_dependencies(monkeypatch):
    FakeMSS.instances.clear()
    monkeypatch.setattr(screen_monitor, "mss", SimpleNamespace(mss=FakeMSS))
    monkeypatch.setattr(screen_monitor, "Image", Image)
    monkeypatch.setattr(screen_monitor, "np", __import__("numpy"))


def test_screen_monitor_grabs_selected_monitor_and_scales():
    monitor = ScreenMonitor(monitor_index=2, scale=0.5)

    image = monitor._grab_scaled()

    assert FakeMSS.instances[-1].grab_calls == [FakeMSS.instances[-1].monitors[2]]
    assert image.size == (2, 1)


def test_screen_monitor_rejects_out_of_range_monitor():
    monitor = ScreenMonitor(monitor_index=9, scale=1)

    with pytest.raises(IndexError, match="out of range"):
        monitor._grab_scaled()


def test_screen_monitor_is_media_displayed_returns_rms_and_image():
    monitor = ScreenMonitor(monitor_index=1, scale=1)

    rms, image = monitor.is_media_displayed()

    assert rms > 0
    assert image.size == (4, 2)


def test_screen_monitor_close_closes_mss():
    monitor = ScreenMonitor(monitor_index=1)
    sct = monitor.sct

    monitor.close()

    assert sct.closed is True


def test_window_monitor_finds_window_by_substring(monkeypatch):
    monkeypatch.setattr(screen_monitor, "win32gui", FakeWin32Gui({1: "JW Library - Media"}))
    monitor = WindowMonitor("library", scale=1)

    assert monitor._find_window_rect() == 1


def test_window_monitor_exact_match(monkeypatch):
    monkeypatch.setattr(screen_monitor, "win32gui", FakeWin32Gui({1: "JW Library - Media", 2: "JW Library"}))
    monitor = WindowMonitor("JW Library", scale=1, exact=True)

    assert monitor._find_window_rect() == 2


def test_window_monitor_raises_when_window_missing(monkeypatch):
    monkeypatch.setattr(screen_monitor, "win32gui", FakeWin32Gui({1: "Other"}))
    monitor = WindowMonitor("JW Library", scale=1)

    with pytest.raises(RuntimeError, match="Could not find window"):
        monitor._grab_scaled()


def test_window_monitor_uses_client_rect(monkeypatch):
    fake_win32 = FakeWin32Gui({1: "JW Library"})
    monkeypatch.setattr(screen_monitor, "win32gui", fake_win32)
    monitor = WindowMonitor("JW Library", scale=1)

    image = monitor._grab_scaled()

    assert image.size == (40, 30)
    assert monitor.sct.grab_calls == [{"left": 10, "top": 20, "width": 40, "height": 30}]


def test_window_monitor_falls_back_to_window_rect(monkeypatch):
    fake_win32 = FakeWin32Gui({1: "JW Library"}, client_fails=True, rect=(5, 6, 25, 16))
    monkeypatch.setattr(screen_monitor, "win32gui", fake_win32)
    monitor = WindowMonitor("JW Library", scale=1)

    image = monitor._grab_scaled()

    assert image.size == (20, 10)
    assert monitor.sct.grab_calls == [{"left": 5, "top": 6, "width": 20, "height": 10}]


def test_window_monitor_rejects_invalid_rect(monkeypatch):
    fake_win32 = FakeWin32Gui({1: "JW Library"}, client_fails=True, rect=(5, 6, 5, 16))
    monkeypatch.setattr(screen_monitor, "win32gui", fake_win32)
    monitor = WindowMonitor("JW Library", scale=1)

    with pytest.raises(RuntimeError, match="invalid size"):
        monitor._grab_scaled()
