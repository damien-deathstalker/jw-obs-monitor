"""Entry point for jw-obs-monitor."""
import logging
import threading
import time
import json
import os
import base64
from io import BytesIO
from pathlib import Path

import flet as ft

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    Image = None
    _PIL_AVAILABLE = False

try:
    import numpy as np
    _NP_AVAILABLE = True
except Exception:
    np = None
    _NP_AVAILABLE = False

# Assuming these exist in your project:
from config import (
    RMS_THRESHOLD, BASELINE_RMS_DELTA, PRESENCE_FRAMES_REQUIRED, ABSENCE_FRAMES_REQUIRED, POLL_INTERVAL,
    OBS_HOST, OBS_PORT, OBS_PASSWORD,
)
from screen_monitor import ScreenMonitor, WindowMonitor
from obs_controller import OBSController
from detector import DetectorWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("jw-obs-ui")


class App:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "JW OBS Monitor"
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.padding = 20
        self.page.window_width = 900
        self.page.window_height = 700

        self.worker = None
        self.obs_controller = None
        self.preview_monitor = None
        self.preview_rms = None
        self.baseline_rms = None

        self._build_ui()
        self._load_obs_config()
        self._update_ui()

    def _build_ui(self):
        # --- LEFT COLUMN: Configuration ---
        
        # 1. Capture Settings
        self.capture_var = ft.RadioGroup(
            value="monitor",
            on_change=self._update_ui,
            content=ft.Row([
                ft.Radio(value="monitor", label="Monitor"),
                ft.Radio(value="window", label="Window Title")
            ])
        )
        
        self.monitor_idx = ft.TextField(label="Monitor index (1-based)", value="2", width=150, height=50)
        self.window_title = ft.TextField(label="Window title", value="JW Library", expand=True, height=50)
        self.exact_match = ft.Checkbox(label="Exact title match", value=False)
        self.scene_name = ft.TextField(label="Media scene name", value="Media", expand=True, height=50)
        self.threshold = ft.TextField(label="RMS threshold", value=str(RMS_THRESHOLD), width=150, height=50)
        self.baseline_delta = ft.TextField(label="Baseline RMS delta", value=str(BASELINE_RMS_DELTA), width=150, height=50)

        capture_card = ft.Card(
            content=ft.Container(
                padding=15,
                content=ft.Column([
                    ft.Text("Capture Settings", size=18, weight=ft.FontWeight.BOLD),
                    self.capture_var,
                    ft.Row([self.monitor_idx, self.window_title]),
                    self.exact_match,
                    ft.Divider(),
                    ft.Row([self.scene_name, self.threshold]),
                    ft.Row([self.baseline_delta])
                ])
            )
        )

        # 2. OBS Connection Settings
        self.obs_host = ft.TextField(label="OBS host", value=OBS_HOST, expand=True, height=50)
        self.obs_port = ft.TextField(label="Port", value=str(OBS_PORT), width=100, height=50)
        self.obs_password = ft.TextField(label="OBS password", value=OBS_PASSWORD, password=True, can_reveal_password=True, expand=True, height=50)
        self.obs_status_var = ft.Text("OBS: disconnected", color=ft.Colors.RED_400)

        obs_card = ft.Card(
            content=ft.Container(
                padding=15,
                content=ft.Column([
                    ft.Text("OBS Settings", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([self.obs_host, self.obs_port]),
                    ft.Row([
                        self.obs_password, 
                        ft.Button("Save", on_click=self._save_obs_config)
                    ]),
                    ft.Row([
                        self.obs_status_var,
                        ft.Container(expand=True), # Spacer
                        ft.FilledButton("Connect OBS", icon=ft.Icons.CABLE, on_click=self._connect_obs)
                    ])
                ])
            )
        )

        # --- RIGHT COLUMN: Dashboard & Preview ---
        
        # Run Controls
        self.status_var = ft.Text("Idle", size=16, weight=ft.FontWeight.W_500)
        self.rms_var = ft.Text("RMS: -", size=14, color=ft.Colors.GREY_400)
        
        self.start_btn = ft.FilledButton("Start", icon=ft.Icons.PLAY_ARROW, style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700), on_click=self.start)
        self.stop_btn = ft.FilledButton("Stop", icon=ft.Icons.STOP, style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700), on_click=self.stop, disabled=True)

        controls_card = ft.Card(
            content=ft.Container(
                padding=15,
                content=ft.Column([
                    ft.Text("Monitoring", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([self.start_btn, self.stop_btn]),
                    ft.Divider(),
                    ft.Text("Status:", weight=ft.FontWeight.BOLD),
                    self.status_var,
                    self.rms_var
                ])
            )
        )

        # Preview Area
        self.preview_image = ft.Image(
            src=self.preview_monitor,
            width=320,
            height=180,
            fit=ft.BoxFit.CONTAIN,
            visible=False
        )
        self.preview_placeholder = ft.Text("Preview unavailable", color=ft.Colors.GREY_500)
        
        preview_box = ft.Container(
            width=340,
            height=190,
            border=ft.Border.all(1, ft.Colors.OUTLINE),
            border_radius=5,
            alignment=ft.Alignment.CENTER,
            content=ft.Stack([
                ft.Container(self.preview_placeholder, alignment=ft.Alignment.CENTER),
                self.preview_image
            ])
        )

        self.preview_rms_text = ft.Text("Preview RMS: -", size=13, color=ft.Colors.GREY_400)
        self.baseline_rms_text = ft.Text("Baseline RMS: -", size=13, color=ft.Colors.GREY_400)

        preview_card = ft.Card(
            content=ft.Container(
                padding=15,
                content=ft.Column([
                    ft.Text("Capture Preview", size=18, weight=ft.FontWeight.BOLD),
                    preview_box,
                    ft.Row([
                        ft.FilledButton("Preview Capture", icon=ft.Icons.CAMERA_ALT, on_click=self._preview_capture),
                        ft.FilledButton("Set baseline", icon=ft.Icons.SAVE, on_click=self._set_baseline),
                    ], spacing=10),
                    self.preview_rms_text,
                    self.baseline_rms_text,
                ])
            )
        )

        # --- Assemble Layout ---
        main_row = ft.Row(
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Column([capture_card, obs_card], expand=5), # Left side takes slightly more space
                ft.Column([controls_card, preview_card], expand=4) # Right side
            ]
        )
        self.page.add(main_row)

    # --- UI Helpers ---
    def _show_toast(self, message, is_error=False):
        color = ft.Colors.RED_600 if is_error else ft.Colors.GREEN_600
        try:
            self.page.bottom_appbar = ft.SnackBar(ft.Text(message), bgcolor=color, open=True)
            self.page.update()
        except Exception:
            print(message)

    def _update_ui(self):
        method = self.capture_var.value
        if method == "monitor":
            self.monitor_idx.disabled = False
            self.window_title.disabled = True
        else:
            self.monitor_idx.disabled = True
            self.window_title.disabled = False
        self.page.update()

    # --- Config Logic ---
    def _obs_config_path(self):
        return Path(os.path.expanduser('~')) / '.jw_obs_monitor.json'

    def _save_obs_config(self, e):
        cfg = {
            'obs_host': self.obs_host.value.strip(),
            'obs_port': self.obs_port.value.strip(),
            'obs_password': self.obs_password.value,
            'threshold': self.threshold.value.strip(),
            'baseline_rms': self.baseline_rms,
            'baseline_rms_delta': self.baseline_delta.value.strip(),
        }
        try:
            p = self._obs_config_path()
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(cfg, f)
            self._show_toast(f"OBS config saved to {p}")
        except Exception as err:
            self._show_toast(f"Failed to save OBS config: {err}", is_error=True)

    def _load_obs_config(self):
        p = self._obs_config_path()
        if not p.exists():
            return
        try:
            with open(p, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            if 'obs_host' in cfg:
                self.obs_host.value = cfg.get('obs_host', self.obs_host.value)
            if 'obs_port' in cfg:
                self.obs_port.value = str(cfg.get('obs_port', self.obs_port.value))
            if 'obs_password' in cfg:
                self.obs_password.value = cfg.get('obs_password', self.obs_password.value)
            if 'threshold' in cfg:
                self.threshold.value = str(cfg.get('threshold', self.threshold.value))
            if 'baseline_rms' in cfg and cfg.get('baseline_rms') is not None:
                self.baseline_rms = float(cfg['baseline_rms'])
                self.baseline_rms_text.value = f"Baseline RMS: {self.baseline_rms:.2f}"
            if 'baseline_rms_delta' in cfg:
                self.baseline_delta.value = str(cfg.get('baseline_rms_delta', self.baseline_delta.value))
            
            self.obs_status_var.value = f"Loaded OBS config from {p}"
            self.obs_status_var.color = ft.Colors.GREY_400
            self.page.update()
        except Exception as err:
            logger.exception('Failed to load OBS config: %s', err)

    # --- Backend Interfacing ---
    def _prepare_preview_monitor(self):
        method = self.capture_var.value
        try:
            if method == "monitor":
                idx = int(self.monitor_idx.value)
                self.preview_monitor = ScreenMonitor(monitor_index=idx, scale=0.25)
            else:
                title = self.window_title.value.strip()
                if not title:
                    raise ValueError("Please enter a window title")
                self.preview_monitor = WindowMonitor(window_title=title, scale=0.25, exact=self.exact_match.value)
            return True
        except Exception as err:
            self.preview_monitor = None
            self._show_toast(f"Failed to create preview monitor: {err}", is_error=True)
            return False

    def _preview_capture(self, e):
        if not self._prepare_preview_monitor():
            return
        self._refresh_preview()

    def _set_baseline(self, e):
        if self.preview_monitor is None and not self._prepare_preview_monitor():
            return

        try:
            rms, _ = self.preview_monitor.is_media_displayed()
            self.baseline_rms = rms
            self.baseline_rms_text.value = f"Baseline RMS: {rms:.2f}"
            self._show_toast("Baseline RMS saved from preview")
            self.page.update()
        except Exception as err:
            self._show_toast(f"Failed to set baseline: {err}", is_error=True)

    def _connect_obs(self, e):
        host = self.obs_host.value.strip() or "localhost"
        try:
            port = int(self.obs_port.value)
        except Exception:
            self._show_toast("Invalid OBS port", is_error=True)
            return
        password = self.obs_password.value

        controller = OBSController(host=host, port=port, password=password)
        try:
            controller.connect()
            self.obs_controller = controller
            self.obs_status_var.value = f"OBS connected to {host}:{port}"
            self.obs_status_var.color = ft.Colors.GREEN_400
            self.status_var.value = "OBS connected"
        except Exception as err:
            self.obs_controller = None
            self.obs_status_var.value = "OBS disconnected"
            self.obs_status_var.color = ft.Colors.RED_400
            self._show_toast(f"OBS connection failed: {err}", is_error=True)
        self.page.update()

    def _refresh_preview(self):
        if self.preview_monitor is None or not _PIL_AVAILABLE:
            self.preview_placeholder.visible = True
            self.preview_image.visible = False
            self.preview_rms_text.value = "Preview RMS: -"
            self.page.update()
            return

        try:
            rms, img = self.preview_monitor.is_media_displayed()
            self.preview_rms = rms
            self.preview_rms_text.value = f"Preview RMS: {rms:.2f}"
            if img is not None:
                preview = img.resize((320, 180), Image.BILINEAR)
                buffered = BytesIO()
                preview.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

                self.preview_image.src = img_str
                self.preview_image.visible = True
                self.preview_placeholder.visible = False
            else:
                self.preview_placeholder.visible = True
                self.preview_image.visible = False
        except Exception as err:
            self._show_toast(f"Preview unavailable: {err}", is_error=True)
            self.preview_placeholder.visible = True
            self.preview_image.visible = False
            self.preview_rms_text.value = "Preview RMS: -"
        self.page.update()

    def _status_update(self, data):
        # Flet allows UI updates from background threads safely
        status = data.get("status")
        if status:
            self.status_var.value = status
            
        rms = data.get("rms")
        if rms is not None:
            self.rms_var.value = f"RMS: {rms}"
            
        present = data.get("present")
        if present is not None:
            if present:
                self.status_var.value = "Media present"
            else:
                if not data.get("status"):
                    self.status_var.value = "Monitoring"
                    
        self.page.update()

    def _monitor_worker_state(self):
        """Background thread to watch for worker crashes/exits."""
        while self.worker and self.worker.is_alive():
            time.sleep(1)
        
        # Worker has stopped
        self.worker = None
        self.start_btn.disabled = False
        self.stop_btn.disabled = True
        if self.status_var.value != "Stopped":
            self.status_var.value = "Stopped"
        self.page.update()

    def start(self, e):
        if self.worker and self.worker.is_alive():
            self._show_toast("Already running")
            return
            
        method = self.capture_var.value
        try:
            threshold = float(self.threshold.value)
        except Exception:
            self._show_toast("Invalid threshold", is_error=True)
            return
            
        scene = self.scene_name.value.strip() or None
        if not scene:
            self._show_toast("Please enter a scene name for media", is_error=True)
            return

        if not self._prepare_preview_monitor():
            return
            
        try:
            if method == "monitor":
                idx = int(self.monitor_idx.value)
                monitor_obj = ScreenMonitor(monitor_index=idx, scale=0.25)
            else:
                title = self.window_title.value.strip()
                if not title:
                    self._show_toast("Please enter a window title", is_error=True)
                    return
                monitor_obj = WindowMonitor(window_title=title, scale=0.25, exact=self.exact_match.value)
        except Exception as err:
            self.preview_monitor = None
            self.status_var.value = "Monitor setup failed"
            self._show_toast(f"Failed to create monitor: {err}", is_error=True)
            self.page.update()
            return

        obs_controller = self.obs_controller if self.obs_controller and self.obs_controller.is_connected() else None
        obs_host = self.obs_host.value.strip()
        try:
            obs_port = int(self.obs_port.value)
        except Exception:
            self._show_toast("Invalid OBS port", is_error=True)
            return
        obs_password = self.obs_password.value

        try:
            baseline_delta = float(self.baseline_delta.value)
        except Exception:
            self._show_toast("Invalid baseline delta", is_error=True)
            return

        self.worker = DetectorWorker(
            monitor_obj=monitor_obj,
            media_scene=scene,
            threshold=threshold,
            presence_req=PRESENCE_FRAMES_REQUIRED,
            absence_req=ABSENCE_FRAMES_REQUIRED,
            poll_interval=POLL_INTERVAL,
            obs_controller=obs_controller,
            obs_host=obs_host,
            obs_port=obs_port,
            obs_password=obs_password,
            baseline_rms=self.baseline_rms,
            baseline_rms_delta=baseline_delta,
            update_cb=self._status_update,
        )
        self.worker.start()
        
        self.start_btn.disabled = True
        self.stop_btn.disabled = False
        self.status_var.value = "Started"
        self.page.update()
        
        # Start background thread to watch the worker
        threading.Thread(target=self._monitor_worker_state, daemon=True).start()

    def stop(self, e):
        if not self.worker:
            return
        self.worker.stop()
        self.worker.join(timeout=5)
        self.worker = None
        self.preview_monitor = None
        
        self.start_btn.disabled = False
        self.stop_btn.disabled = True
        self.status_var.value = "Stopped"
        self.page.update()


def main(page: ft.Page):
    App(page)


if __name__ == "__main__":
    ft.run(main)