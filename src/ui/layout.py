"""Flet layout construction for the monitor app."""

from dataclasses import dataclass

import flet as ft


@dataclass
class UiControls:
    capture_var: ft.RadioGroup
    monitor_idx: ft.TextField
    window_title: ft.TextField
    exact_match: ft.Checkbox
    scene_name: ft.TextField
    threshold: ft.TextField
    baseline_delta: ft.TextField
    obs_host: ft.TextField
    obs_port: ft.TextField
    obs_password: ft.TextField
    obs_status_var: ft.Text
    status_var: ft.Text
    rms_var: ft.Text
    start_btn: ft.FilledButton
    stop_btn: ft.FilledButton
    preview_image: ft.Image
    preview_placeholder: ft.Text
    preview_box: ft.Container
    preview_rms_text: ft.Text
    baseline_rms_text: ft.Text
    main_content: ft.Container
    root: ft.Column


class AppLayout:
    def __init__(
        self,
        callbacks,
        min_content_width,
        rms_threshold,
        baseline_rms_delta,
        obs_host,
        obs_port,
        obs_password,
    ):
        self.callbacks = callbacks
        self.min_content_width = min_content_width
        self.rms_threshold = rms_threshold
        self.baseline_rms_delta = baseline_rms_delta
        self.obs_host = obs_host
        self.obs_port = obs_port
        self.obs_password = obs_password

    def build(self):
        capture_var = ft.RadioGroup(
            value="monitor",
            on_change=self.callbacks.update_ui,
            content=ft.Row([
                ft.Radio(value="monitor", label="Monitor"),
                ft.Radio(value="window", label="Window Title"),
            ]),
        )

        monitor_idx = ft.TextField(label="Monitor index (1-based)", value="2", width=150, height=50)
        window_title = ft.TextField(label="Window title", value="JW Library", expand=True, height=50)
        exact_match = ft.Checkbox(label="Exact title match", value=False)
        scene_name = ft.TextField(label="Media scene name", value="Media", expand=True, height=50)
        threshold = ft.TextField(label="RMS threshold", value=str(self.rms_threshold), width=150, height=50)
        baseline_delta = ft.TextField(label="Baseline RMS delta", value=str(self.baseline_rms_delta), width=150, height=50)

        capture_card = self._capture_card(
            capture_var,
            monitor_idx,
            window_title,
            exact_match,
            scene_name,
            threshold,
            baseline_delta,
        )

        obs_host = ft.TextField(label="OBS host", value=self.obs_host, expand=True, height=50)
        obs_port = ft.TextField(label="Port", value=str(self.obs_port), width=100, height=50)
        obs_password = ft.TextField(
            label="OBS password",
            value=self.obs_password,
            password=True,
            can_reveal_password=True,
            expand=True,
            height=50,
        )
        obs_status_var = ft.Text("OBS: disconnected", color=ft.Colors.RED_400)
        obs_card = self._obs_card(obs_host, obs_port, obs_password, obs_status_var)

        status_var = ft.Text("Idle", size=16, weight=ft.FontWeight.W_500)
        rms_var = ft.Text("RMS: -", size=14, color=ft.Colors.GREY_400)
        start_btn = ft.FilledButton(
            "Start",
            icon=ft.Icons.PLAY_ARROW,
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700),
            on_click=self.callbacks.start,
        )
        stop_btn = ft.FilledButton(
            "Stop",
            icon=ft.Icons.STOP,
            style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700),
            on_click=self.callbacks.stop,
            disabled=True,
        )
        controls_card = self._controls_card(start_btn, stop_btn, status_var, rms_var)

        preview_image = ft.Image(src=None, fit=ft.BoxFit.CONTAIN, visible=False, expand=True)
        preview_placeholder = ft.Text("Preview unavailable", color=ft.Colors.GREY_500)
        preview_box = ft.Container(
            border=ft.Border.all(1, ft.Colors.OUTLINE),
            border_radius=5,
            alignment=ft.Alignment.CENTER,
            padding=5,
            content=ft.Stack([
                ft.Container(preview_placeholder, alignment=ft.Alignment.CENTER),
                preview_image,
            ]),
            expand=True,
        )
        preview_rms_text = ft.Text("Preview RMS: -", size=13, color=ft.Colors.GREY_400)
        baseline_rms_text = ft.Text("Baseline RMS: -", size=13, color=ft.Colors.GREY_400)
        preview_card = self._preview_card(preview_box, preview_rms_text, baseline_rms_text)

        main_row = ft.Row(
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Column([capture_card, obs_card], expand=5),
                ft.Column([controls_card, preview_card], expand=4),
            ],
        )
        main_content = ft.Container(content=main_row, width=self.min_content_width)
        root = ft.Column(
            [
                ft.Row(
                    [main_content],
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        return UiControls(
            capture_var=capture_var,
            monitor_idx=monitor_idx,
            window_title=window_title,
            exact_match=exact_match,
            scene_name=scene_name,
            threshold=threshold,
            baseline_delta=baseline_delta,
            obs_host=obs_host,
            obs_port=obs_port,
            obs_password=obs_password,
            obs_status_var=obs_status_var,
            status_var=status_var,
            rms_var=rms_var,
            start_btn=start_btn,
            stop_btn=stop_btn,
            preview_image=preview_image,
            preview_placeholder=preview_placeholder,
            preview_box=preview_box,
            preview_rms_text=preview_rms_text,
            baseline_rms_text=baseline_rms_text,
            main_content=main_content,
            root=root,
        )

    def _capture_card(self, capture_var, monitor_idx, window_title, exact_match, scene_name, threshold, baseline_delta):
        return ft.Card(
            content=ft.Container(
                padding=15,
                content=ft.Column([
                    ft.Text("Capture Settings", size=18, weight=ft.FontWeight.BOLD),
                    capture_var,
                    ft.Row([monitor_idx, window_title]),
                    exact_match,
                    ft.Divider(),
                    ft.Row([scene_name, threshold]),
                    ft.Row([baseline_delta]),
                ]),
            )
        )

    def _obs_card(self, obs_host, obs_port, obs_password, obs_status_var):
        return ft.Card(
            content=ft.Container(
                padding=15,
                content=ft.Column([
                    ft.Text("OBS Settings", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([obs_host, obs_port]),
                    ft.Row([obs_password, ft.Button("Save", on_click=self.callbacks.save_obs_config)]),
                    ft.Row([
                        obs_status_var,
                        ft.Container(expand=True),
                        ft.FilledButton("Connect OBS", icon=ft.Icons.CABLE, on_click=self.callbacks.connect_obs),
                    ]),
                ]),
            )
        )

    def _controls_card(self, start_btn, stop_btn, status_var, rms_var):
        return ft.Card(
            content=ft.Container(
                padding=15,
                content=ft.Column([
                    ft.Text("Monitoring", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([start_btn, stop_btn]),
                    ft.Divider(),
                    ft.Text("Status:", weight=ft.FontWeight.BOLD),
                    status_var,
                    rms_var,
                ]),
            )
        )

    def _preview_card(self, preview_box, preview_rms_text, baseline_rms_text):
        return ft.Card(
            content=ft.Container(
                padding=15,
                content=ft.Column([
                    ft.Text("Capture Preview", size=18, weight=ft.FontWeight.BOLD),
                    preview_box,
                    ft.Row([
                        ft.FilledButton("Preview Capture", icon=ft.Icons.CAMERA_ALT, on_click=self.callbacks.preview_capture),
                        ft.FilledButton("Set baseline", icon=ft.Icons.SAVE, on_click=self.callbacks.set_baseline),
                    ], spacing=10),
                    preview_rms_text,
                    baseline_rms_text,
                ]),
            )
        )
