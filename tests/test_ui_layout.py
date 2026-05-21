from types import SimpleNamespace

import flet as ft

from src.ui.layout import AppLayout, UiControls


def noop(*args, **kwargs):
    return None


def make_callbacks():
    return SimpleNamespace(
        update_ui=noop,
        save_obs_config=noop,
        connect_obs=noop,
        preview_capture=noop,
        set_baseline=noop,
        start=noop,
        stop=noop,
    )


def build_layout():
    return AppLayout(
        callbacks=make_callbacks(),
        min_content_width=860,
        rms_threshold=15.0,
        baseline_rms_delta=7.0,
        obs_host="localhost",
        obs_port=4455,
        obs_password="secret",
    ).build()


def test_layout_builds_all_controls_without_runtime_constructor_errors():
    ui = build_layout()

    assert isinstance(ui, UiControls)
    assert isinstance(ui.root, ft.Column)
    assert isinstance(ui.preview_image, ft.Image)
    assert ui.preview_image.src is None
    assert ui.preview_image.visible is False


def test_layout_sets_expected_default_values():
    ui = build_layout()

    assert ui.capture_var.value == "monitor"
    assert ui.monitor_idx.value == "2"
    assert ui.window_title.value == "JW Library"
    assert ui.scene_name.value == "Media"
    assert ui.threshold.value == "15.0"
    assert ui.baseline_delta.value == "7.0"
    assert ui.obs_host.value == "localhost"
    assert ui.obs_port.value == "4455"
    assert ui.obs_password.value == "secret"
    assert ui.status_var.value == "Idle"
    assert ui.rms_var.value == "RMS: -"


def test_layout_has_horizontal_and_vertical_scrollers():
    ui = build_layout()

    assert ui.root.scroll == ft.ScrollMode.AUTO
    assert ui.root.controls[0].scroll == ft.ScrollMode.AUTO
    assert ui.main_content.width == 860


def test_layout_wires_button_callbacks():
    callbacks = make_callbacks()
    ui = AppLayout(
        callbacks=callbacks,
        min_content_width=860,
        rms_threshold=15.0,
        baseline_rms_delta=7.0,
        obs_host="localhost",
        obs_port=4455,
        obs_password="",
    ).build()

    assert ui.capture_var.on_change is callbacks.update_ui
    assert ui.start_btn.on_click is callbacks.start
    assert ui.stop_btn.on_click is callbacks.stop
