"""Application controller for the Flet UI."""

import base64
import logging
import threading
import time
from io import BytesIO
from types import SimpleNamespace

import flet as ft

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    Image = None
    _PIL_AVAILABLE = False

try:
    from ..config import (
        BASELINE_RMS_DELTA,
        OBS_HOST,
        OBS_PASSWORD,
        OBS_PORT,
        POLL_INTERVAL,
        PRESENCE_FRAMES_REQUIRED,
        ABSENCE_FRAMES_REQUIRED,
        RMS_THRESHOLD,
    )
    from ..detector import DetectorWorker
    from ..obs_controller import OBSController
    from ..screen_monitor import ScreenMonitor, WindowMonitor
except ImportError:
    from config import (
        BASELINE_RMS_DELTA,
        OBS_HOST,
        OBS_PASSWORD,
        OBS_PORT,
        POLL_INTERVAL,
        PRESENCE_FRAMES_REQUIRED,
        ABSENCE_FRAMES_REQUIRED,
        RMS_THRESHOLD,
    )
    from detector import DetectorWorker
    from obs_controller import OBSController
    from screen_monitor import ScreenMonitor, WindowMonitor

from .config_store import load_obs_config, save_obs_config
from .layout import AppLayout

logger = logging.getLogger("jw-obs-ui")


class App:
    def __init__(self, page: ft.Page):
        self.page = page
        self.min_content_width = 860
        self.worker = None
        self.obs_controller = None
        self.preview_monitor = None
        self.preview_rms = None
        self.baseline_rms = None

        self._configure_page()
        self.ui = self._build_ui()
        self.page.add(self.ui.root)
        self._load_obs_config()
        self._update_ui()
        self._bind_resize_handler()

    def _configure_page(self):
        self.page.title = "JW OBS Monitor"
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.padding = 20
        self.page.window.resizable = True

    def _build_ui(self):
        callbacks = SimpleNamespace(
            update_ui=self._update_ui,
            save_obs_config=self._save_obs_config,
            connect_obs=self._connect_obs,
            preview_capture=self._preview_capture,
            set_baseline=self._set_baseline,
            start=self.start,
            stop=self.stop,
        )
        return AppLayout(
            callbacks=callbacks,
            min_content_width=self.min_content_width,
            rms_threshold=RMS_THRESHOLD,
            baseline_rms_delta=BASELINE_RMS_DELTA,
            obs_host=OBS_HOST,
            obs_port=OBS_PORT,
            obs_password=OBS_PASSWORD,
        ).build()

    def _bind_resize_handler(self):
        try:
            self.page.on_resize = self._on_resize
            self._on_resize(None)
        except Exception:
            logger.exception("Failed to bind resize handler")

    def _show_toast(self, message, is_error=False):
        color = ft.Colors.RED_600 if is_error else ft.Colors.GREEN_600
        try:
            self.page.bottom_appbar = ft.SnackBar(ft.Text(message), bgcolor=color, open=True)
            self.page.update()
        except Exception:
            logger.exception("Failed to show toast: %s", message)

    def _update_ui(self, e=None):
        method = self.ui.capture_var.value
        self.ui.monitor_idx.disabled = method != "monitor"
        self.ui.window_title.disabled = method == "monitor"
        self.page.update()

    def _on_resize(self, e):
        try:
            w = int(getattr(self.page, "window_width", None) or getattr(self.page, "width", None))
        except Exception:
            return
        page_padding = int(getattr(self.page, "padding", 0) or 0)
        self.ui.main_content.width = max(self.min_content_width, w - (page_padding * 2))
        self.ui.preview_image.width = max(160, min(320, int(w * 0.35)))
        self.page.update()

    def _close_monitor(self, monitor):
        close = getattr(monitor, "close", None)
        if close:
            try:
                close()
            except Exception:
                logger.exception("Failed to close monitor")

    def _save_obs_config(self, e):
        cfg = {
            "obs_host": self.ui.obs_host.value.strip(),
            "obs_port": self.ui.obs_port.value.strip(),
            "obs_password": self.ui.obs_password.value,
            "threshold": self.ui.threshold.value.strip(),
            "baseline_rms": self.baseline_rms,
            "baseline_rms_delta": self.ui.baseline_delta.value.strip(),
        }
        try:
            path = save_obs_config(cfg)
            self._show_toast(f"OBS config saved to {path} (password is stored locally in plaintext)")
        except Exception as err:
            self._show_toast(f"Failed to save OBS config: {err}", is_error=True)

    def _load_obs_config(self):
        try:
            cfg = load_obs_config()
        except Exception as err:
            logger.exception("Failed to load OBS config: %s", err)
            return
        if not cfg:
            return

        self.ui.obs_host.value = cfg.get("obs_host", self.ui.obs_host.value)
        self.ui.obs_port.value = str(cfg.get("obs_port", self.ui.obs_port.value))
        self.ui.obs_password.value = cfg.get("obs_password", self.ui.obs_password.value)
        self.ui.threshold.value = str(cfg.get("threshold", self.ui.threshold.value))
        self.ui.baseline_delta.value = str(cfg.get("baseline_rms_delta", self.ui.baseline_delta.value))
        if cfg.get("baseline_rms") is not None:
            self.baseline_rms = float(cfg["baseline_rms"])
            self.ui.baseline_rms_text.value = f"Baseline RMS: {self.baseline_rms:.2f}"

        self.ui.obs_status_var.value = "Loaded OBS config"
        self.ui.obs_status_var.color = ft.Colors.GREY_400
        self.page.update()

    def _create_monitor(self):
        method = self.ui.capture_var.value
        if method == "monitor":
            return ScreenMonitor(monitor_index=int(self.ui.monitor_idx.value), scale=0.25)

        title = self.ui.window_title.value.strip()
        if not title:
            raise ValueError("Please enter a window title")
        return WindowMonitor(window_title=title, scale=0.25, exact=self.ui.exact_match.value)

    def _prepare_preview_monitor(self):
        previous_monitor = self.preview_monitor
        try:
            monitor = self._create_monitor()
            self.preview_monitor = monitor
            if previous_monitor is not None and previous_monitor is not monitor:
                self._close_monitor(previous_monitor)
            return True
        except Exception as err:
            self.preview_monitor = None
            self._close_monitor(previous_monitor)
            self._show_toast(f"Failed to create preview monitor: {err}", is_error=True)
            return False

    def _preview_capture(self, e):
        if self._prepare_preview_monitor():
            self._refresh_preview()

    def _set_baseline(self, e):
        if self.preview_monitor is None and not self._prepare_preview_monitor():
            return
        try:
            rms, _ = self.preview_monitor.is_media_displayed()
            self.baseline_rms = rms
            self.ui.baseline_rms_text.value = f"Baseline RMS: {rms:.2f}"
            self._show_toast("Baseline RMS saved from preview")
            self.page.update()
        except Exception as err:
            self._show_toast(f"Failed to set baseline: {err}", is_error=True)

    def _connect_obs(self, e):
        host = self.ui.obs_host.value.strip() or "localhost"
        try:
            port = int(self.ui.obs_port.value)
        except Exception:
            self._show_toast("Invalid OBS port", is_error=True)
            return

        controller = OBSController(host=host, port=port, password=self.ui.obs_password.value)
        try:
            controller.connect()
            self.obs_controller = controller
            self.ui.obs_status_var.value = f"OBS connected to {host}:{port}"
            self.ui.obs_status_var.color = ft.Colors.GREEN_400
            self.ui.status_var.value = "OBS connected"
        except Exception as err:
            self.obs_controller = None
            self.ui.obs_status_var.value = "OBS disconnected"
            self.ui.obs_status_var.color = ft.Colors.RED_400
            self._show_toast(f"OBS connection failed: {err}", is_error=True)
        self.page.update()

    def _refresh_preview(self):
        if self.preview_monitor is None or not _PIL_AVAILABLE:
            self.ui.preview_placeholder.visible = True
            self.ui.preview_image.visible = False
            self.ui.preview_rms_text.value = "Preview RMS: -"
            self.page.update()
            return

        try:
            rms, img = self.preview_monitor.is_media_displayed()
            self.preview_rms = rms
            self.ui.preview_rms_text.value = f"Preview RMS: {rms:.2f}"
            if img is not None:
                preview = img.resize((320, 180), Image.BILINEAR)
                buffered = BytesIO()
                preview.save(buffered, format="PNG")
                self.ui.preview_image.src = base64.b64encode(buffered.getvalue()).decode("utf-8")
                self.ui.preview_image.visible = True
                self.ui.preview_placeholder.visible = False
            else:
                self.ui.preview_placeholder.visible = True
                self.ui.preview_image.visible = False
        except Exception as err:
            self._show_toast(f"Preview unavailable: {err}", is_error=True)
            self.ui.preview_placeholder.visible = True
            self.ui.preview_image.visible = False
            self.ui.preview_rms_text.value = "Preview RMS: -"
        self.page.update()

    def _status_update(self, data):
        status = data.get("status")
        if status:
            self.ui.status_var.value = status

        rms = data.get("rms")
        if rms is not None:
            self.ui.rms_var.value = f"RMS: {rms}"

        present = data.get("present")
        if present is not None:
            if present:
                self.ui.status_var.value = "Media present"
            elif not data.get("status"):
                self.ui.status_var.value = "Monitoring"

        self.page.update()

    def _monitor_worker_state(self, worker):
        while worker.is_alive():
            time.sleep(1)

        if self.worker is not worker:
            return
        self.worker = None
        self.ui.start_btn.disabled = False
        self.ui.stop_btn.disabled = True
        if self.ui.status_var.value != "Stopped":
            self.ui.status_var.value = "Stopped"
        self.page.update()

    def start(self, e):
        if self.worker and self.worker.is_alive():
            self._show_toast("Already running")
            return

        scene = self.ui.scene_name.value.strip()
        if not scene:
            self._show_toast("Please enter a scene name for media", is_error=True)
            return

        try:
            threshold = float(self.ui.threshold.value)
            baseline_delta = float(self.ui.baseline_delta.value)
            obs_port = int(self.ui.obs_port.value)
            monitor_obj = self._create_monitor()
        except Exception as err:
            self._show_toast(f"Invalid settings: {err}", is_error=True)
            return

        obs_controller = self.obs_controller if self.obs_controller and self.obs_controller.is_connected() else None
        worker = DetectorWorker(
            monitor_obj=monitor_obj,
            media_scene=scene,
            threshold=threshold,
            presence_req=PRESENCE_FRAMES_REQUIRED,
            absence_req=ABSENCE_FRAMES_REQUIRED,
            poll_interval=POLL_INTERVAL,
            obs_controller=obs_controller,
            obs_host=self.ui.obs_host.value.strip(),
            obs_port=obs_port,
            obs_password=self.ui.obs_password.value,
            baseline_rms=self.baseline_rms,
            baseline_rms_delta=baseline_delta,
            update_cb=self._status_update,
        )
        self.worker = worker
        worker.start()

        self.ui.start_btn.disabled = True
        self.ui.stop_btn.disabled = False
        self.ui.status_var.value = "Started"
        self.page.update()
        threading.Thread(target=self._monitor_worker_state, args=(worker,), daemon=True).start()

    def stop(self, e):
        if not self.worker:
            return
        worker = self.worker
        worker.stop()
        worker.join(timeout=5)
        if self.worker is worker and not worker.is_alive():
            self.worker = None
        self._close_monitor(self.preview_monitor)
        self.preview_monitor = None

        self.ui.start_btn.disabled = False
        self.ui.stop_btn.disabled = True
        self.ui.status_var.value = "Stopped"
        self.page.update()
