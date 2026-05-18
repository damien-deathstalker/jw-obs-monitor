import logging
try:
    import obsws_python as obs
    _HAS_OWP = True
except Exception:
    _HAS_OWP = False


class OBSController:
    def __init__(self, host="localhost", port=4455, password=""):
        self.host = host
        self.port = port
        self.password = password
        self.client = None
        self.prev_scene = None
        self.logger = logging.getLogger("OBSController")

    def connect(self):
        if not _HAS_OWP:
            raise RuntimeError("obsws_python library not available. Install obsws-python")
        try:
            self.client = obs.ReqClient(host=self.host, port=self.port, password=self.password)
            self.logger.info("Connected to OBS WebSocket at %s:%s", self.host, self.port)
        except Exception as e:
            self.logger.exception("Failed to connect to OBS: %s", e)
            raise

    def disconnect(self):
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
            finally:
                self.client = None

    def is_connected(self):
        return self.client is not None

    def get_current_scene(self):
        if not self.client:
            return None
        try:
            response = self.client.get_current_program_scene()
            return response.current_program_scene_name
        except Exception:
            self.logger.exception("Failed to get current scene")
            return None

    def set_scene(self, scene_name):
        if not self.client:
            raise RuntimeError("Not connected to OBS WebSocket")
        try:
            self.client.set_current_program_scene(scene_name)
        except Exception as e:
            self.logger.exception("Failed to set scene %s: %s", scene_name, e)
            raise

    def switch_to_media_scene(self, media_scene):
        try:
            current = self.get_current_scene()
            self.prev_scene = current
        except Exception:
            self.prev_scene = None
        if media_scene:
            self.client.set_current_program_scene(media_scene)

    def revert_scene(self):
        if self.prev_scene:
            try:
                self.client.set_current_program_scene(self.prev_scene)
            except Exception:
                self.logger.exception("Failed to revert to previous scene")
            finally:
                self.prev_scene = None