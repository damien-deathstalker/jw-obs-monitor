from time import time

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    import mss
except ImportError:
    mss = None

class ScreenMonitor:
    """Capture a given monitor and provide a simple RMS-based content metric.

    monitor_index is 1-based index into mss.monitors (1..len-1). scale reduces
    image size to speed up processing.
    """
    def __init__(self, monitor_index=2, scale=0.25):
        self.monitor_index = monitor_index
        self.scale = scale
        if mss is None:
            raise RuntimeError("Screen capture requires the mss package")
        if Image is None:
            raise RuntimeError("Screen capture requires Pillow")
        if np is None:
            raise RuntimeError("Screen capture requires numpy")
        self.sct = mss.mss()

    def _grab_scaled(self):
        monitors = self.sct.monitors
        if self.monitor_index < 1 or self.monitor_index >= len(monitors):
            raise IndexError(f"monitor_index {self.monitor_index} out of range (1..{len(monitors)-1})")
        mon = monitors[self.monitor_index]
        img = self.sct.grab(mon)
        im = Image.frombytes("RGB", img.size, img.rgb)
        if self.scale and self.scale != 1.0:
            new_size = (max(1, int(img.width * self.scale)), max(1, int(img.height * self.scale)))
            im = im.resize(new_size, Image.BILINEAR)
        return im

    @staticmethod
    def _rms(pil_image):
        """Compute RMS (root mean square) of grayscale image intensities."""
        gray = pil_image.convert("L")
        arr = np.asarray(gray, dtype=np.float32)
        mean = arr.mean()
        rms = float(np.sqrt(np.mean((arr - mean) ** 2)))
        return rms

    def is_media_displayed(self):
        """Capture the monitor and return (rms_value, pil_image).

        This method only captures and computes RMS; decision thresholds are
        applied by the caller (so config is not required here).
        """
        im = self._grab_scaled()
        rms = self._rms(im)
        return rms, im


# Window-based monitor for Windows OS. Uses Win32 APIs to find a window by title
# substring and captures its bounding rectangle.
try:
    import win32gui
except Exception:
    win32gui = None


class WindowMonitor:
    """Capture a specific top-level window by title substring (Windows only).

    Parameters
    - window_title: substring to match against window titles (case-insensitive)
    - scale: downscale factor for processing speed
    - exact: if True, requires exact match of the window title
    """

    def __init__(self, window_title, scale=0.25, exact=False):
        if win32gui is None:
            raise RuntimeError("Window capture requires pywin32 (win32gui)")
        if mss is None:
            raise RuntimeError("Window capture requires the mss package")
        if Image is None:
            raise RuntimeError("Window capture requires Pillow")
        if np is None:
            raise RuntimeError("Window capture requires numpy")
        self.window_title = window_title
        self.scale = scale
        self.exact = exact
        self.sct = mss.mss()

    def _find_window_rect(self):
        """Find a top-level window whose title matches the configured substring.
        Returns the matching window handle (hwnd) or None if not found.
        """
        target = self.window_title.lower() if self.window_title else None
        result = None

        def _enum(hwnd, _):
            nonlocal result
            if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return True
            t = title.lower().strip()
            if self.exact:
                if t == target:
                    result = hwnd
                    return False
            else:
                if target in t:
                    result = hwnd
                    return False
            return True

        win32gui.EnumWindows(_enum, None)
        return result

    def _grab_scaled(self):
        hwnd = self._find_window_rect()
        if hwnd is None:
            raise RuntimeError(f"Could not find window matching '{self.window_title}'")

        # Prefer the client area (content) rather than the outer window frame
        try:
            client_rect = win32gui.GetClientRect(hwnd)
            left_top = win32gui.ClientToScreen(hwnd, (client_rect[0], client_rect[1]))
            right_bottom = win32gui.ClientToScreen(hwnd, (client_rect[2], client_rect[3]))
            left, top = left_top
            right, bottom = right_bottom
        except Exception:
            # fallback to window rect
            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect

        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            raise RuntimeError("Found window has invalid size")
        bbox = {"left": left, "top": top, "width": width, "height": height}
        img = self.sct.grab(bbox)
        im = Image.frombytes("RGB", img.size, img.rgb)
        if self.scale and self.scale != 1.0:
            new_size = (max(1, int(img.width * self.scale)), max(1, int(img.height * self.scale)))
            im = im.resize(new_size, Image.BILINEAR)
        return im

    @staticmethod
    def _rms(pil_image):
        gray = pil_image.convert("L")
        arr = np.asarray(gray, dtype=np.float32)
        mean = arr.mean()
        rms = float(np.sqrt(np.mean((arr - mean) ** 2)))
        return rms

    def is_media_displayed(self):
        im = self._grab_scaled()
        rms = self._rms(im)
        return rms, im