import threading
import time
import logging

try:
    import numpy as np
    _NP_AVAILABLE = True
except Exception:
    np = None
    _NP_AVAILABLE = False

try:
    from PIL import ImageStat
except Exception:
    ImageStat = None

from config import BASELINE_RMS_DELTA
from obs_controller import OBSController

logger = logging.getLogger("jw-obs-worker")


class DetectorWorker(threading.Thread):
    def __init__(self, monitor_obj, media_scene, threshold, presence_req, absence_req, poll_interval,
                 obs_controller=None, obs_host=None, obs_port=None, obs_password=None, update_cb=None,
                 baseline_rms=None, baseline_rms_delta=BASELINE_RMS_DELTA):
        super().__init__(daemon=True)
        self.monitor = monitor_obj
        self.media_scene = media_scene
        self.threshold = threshold
        self.presence_req = presence_req
        self.absence_req = absence_req
        self.poll_interval = poll_interval
        self.update_cb = update_cb
        self.baseline_rms = baseline_rms
        self.baseline_rms_delta = baseline_rms_delta
        self._stop_event = threading.Event()
        self.obs_controller = obs_controller
        if self.obs_controller is not None:
            self.obs = self.obs_controller
        else:
            self.obs = OBSController(host=obs_host, port=obs_port, password=obs_password)
        # baseline values for JW default (black background, white text)
        self._baseline_set = False
        self._baseline_rms = None
        self._baseline_mean = None
        self._baseline_bright = None
        self._baseline_samples = []
        self._baseline_sample_target = 5

        if self.baseline_rms is not None:
            self._baseline_rms = float(self.baseline_rms)
            self._baseline_set = True

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def _notify(self, **kwargs):
        if self.update_cb:
            try:
                self.update_cb(kwargs)
            except Exception:
                logger.exception("Update callback failed")

    def run(self):
        presence_count = 0
        absence_count = 0
        media_active = False

        # Try connect to OBS
        if self.obs_controller is None or not self.obs.is_connected():
            try:
                self.obs.connect()
            except Exception as e:
                logger.warning("Could not connect to OBS: %s", e)
                self._notify(status=f"OBS connect failed: {e}")

        while not self.stopped():
            try:
                rms, img = self.monitor.is_media_displayed()
                mean = None
                bright_frac = None
                if img is not None:
                    if _NP_AVAILABLE:
                        try:
                            arr = np.asarray(img.convert('L'), dtype=np.uint8)
                            mean = float(arr.mean())
                            bright_frac = float((arr > 200).sum()) / float(arr.size)
                        except Exception:
                            mean = None
                            bright_frac = None
                    else:
                        try:
                            if ImageStat is not None:
                                gray = img.convert('L')
                                stat = ImageStat.Stat(gray)
                                mean = float(stat.mean[0])
                                data = list(gray.getdata())
                                total = len(data)
                                bright = sum(1 for v in data if v > 200)
                                bright_frac = float(bright) / float(total) if total > 0 else 0.0
                        except Exception:
                            mean = None
                            bright_frac = None
            except Exception as e:
                logger.debug("Capture error: %s", e)
                rms = 0.0
                img = None
                mean = None
                bright_frac = None

            # accumulate baseline samples from the first visible frames
            if not self._baseline_set and mean is not None:
                try:
                    if bright_frac is None:
                        bright_frac = 0.0
                    self._baseline_samples.append((rms, mean, bright_frac))
                    if len(self._baseline_samples) >= self._baseline_sample_target:
                        self._baseline_rms = sum(r for r, _, _ in self._baseline_samples) / len(self._baseline_samples)
                        self._baseline_mean = sum(m for _, m, _ in self._baseline_samples) / len(self._baseline_samples)
                        self._baseline_bright = sum(b for _, _, b in self._baseline_samples) / len(self._baseline_samples)
                        self._baseline_set = True
                except Exception:
                    pass

            def stats_indicate_media():
                if rms >= self.threshold:
                    return True
                if not self._baseline_set:
                    return False
                if self._baseline_rms is not None and rms >= (self._baseline_rms + self.baseline_rms_delta):
                    return True
                if mean is not None and self._baseline_mean is not None and mean >= (self._baseline_mean + 12):
                    return True
                if bright_frac is not None and self._baseline_bright is not None and bright_frac >= (self._baseline_bright + 0.08):
                    return True
                return False

            def stats_indicate_default():
                if not self._baseline_set or mean is None:
                    return False
                if self._baseline_rms is not None and rms <= (self._baseline_rms + 5):
                    if self._baseline_mean is None or mean <= (self._baseline_mean + 8):
                        if bright_frac is None or self._baseline_bright is None:
                            return True
                        return bright_frac <= (self._baseline_bright + 0.05)
                return False

            present = stats_indicate_media()

            if present:
                presence_count += 1
                absence_count = 0
            else:
                absence_count += 1
                presence_count = 0

            # notifications
            self._notify(rms=round(rms, 2), present=present, p_count=presence_count, a_count=absence_count, media_active=media_active)

            if not media_active and presence_count >= self.presence_req:
                logger.info("Media detected (rms=%.2f) -> switching to media scene", rms)
                try:
                    self.obs.switch_to_media_scene(self.media_scene)
                    media_active = True
                    self._notify(status=f"Switched to {self.media_scene}")
                except Exception as e:
                    logger.warning("Failed to switch to media scene: %s", e)
                    try:
                        self.obs.disconnect()
                        self.obs.connect()
                    except Exception:
                        time.sleep(1)

            if media_active and absence_count >= self.absence_req:
                logger.info("Media no longer detected -> reverting")
                try:
                    self.obs.revert_scene()
                    media_active = False
                    self._notify(status="Reverted scene")
                except Exception as e:
                    logger.warning("Failed to revert scene: %s", e)
                    try:
                        self.obs.disconnect()
                        self.obs.connect()
                    except Exception:
                        time.sleep(1)

            time.sleep(self.poll_interval)

        # cleanup
        try:
            self.obs.disconnect()
        except Exception:
            pass
        self._notify(status="Stopped")
