# Runtime hook to prevent flet from attempting to pip-install flet_desktop at runtime when frozen
import sys
try:
    import flet.utils.pip as _flet_pip
    def _noop(*args, **kwargs):
        return None
    _flet_pip.ensure_flet_desktop_package_installed = _noop
except Exception:
    pass
