from src.ui import App
from src.ui.app import App as AppClass


def test_ui_package_exports_app():
    assert App is AppClass
