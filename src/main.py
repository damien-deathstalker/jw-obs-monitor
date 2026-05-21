"""Entry point for jw-obs-monitor."""

import logging

import flet as ft
import flet_desktop  # noqa: F401 - imported so PyInstaller includes desktop runtime assets.

try:
    from .ui import App
except ImportError:
    from ui import App


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main(page: ft.Page):
    App(page)


if __name__ == "__main__":
    ft.run(main)
