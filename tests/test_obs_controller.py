from types import SimpleNamespace

import pytest

from src.obs_controller import OBSController


class FakeObsClient:
    def __init__(self, host="localhost", port=4455, password=""):
        self.host = host
        self.port = port
        self.password = password
        self.current_scene = "Camera"
        self.disconnected = False

    def disconnect(self):
        self.disconnected = True

    def get_current_program_scene(self):
        return SimpleNamespace(current_program_scene_name=self.current_scene)

    def set_current_program_scene(self, scene_name):
        self.current_scene = scene_name


class FailingDisconnectClient(FakeObsClient):
    def disconnect(self):
        raise RuntimeError("disconnect failed")


class FailingSetSceneClient(FakeObsClient):
    def set_current_program_scene(self, scene_name):
        raise RuntimeError("set failed")


class FailingCurrentSceneClient(FakeObsClient):
    def get_current_program_scene(self):
        raise RuntimeError("scene failed")


def failing_factory(**kwargs):
    raise RuntimeError("connect failed")


def test_connect_uses_injected_client_factory():
    controller = OBSController(client_factory=FakeObsClient)

    controller.connect()

    assert controller.is_connected()
    assert controller.client.host == "localhost"
    assert controller.client.port == 4455


def test_set_scene_requires_connection():
    controller = OBSController(client_factory=FakeObsClient)

    with pytest.raises(RuntimeError, match="Not connected"):
        controller.set_scene("Media")


def test_switch_to_media_scene_stores_previous_scene_and_reverts():
    controller = OBSController(client_factory=FakeObsClient)
    controller.connect()

    controller.switch_to_media_scene("Media")

    assert controller.prev_scene == "Camera"
    assert controller.get_current_scene() == "Media"

    controller.revert_scene()

    assert controller.get_current_scene() == "Camera"
    assert controller.prev_scene is None


def test_transition_scene_is_compatibility_alias():
    controller = OBSController(client_factory=FakeObsClient)
    controller.connect()

    assert controller.transition_scene("Media") is True
    assert controller.get_current_scene() == "Media"


def test_connect_failure_is_raised():
    controller = OBSController(client_factory=failing_factory)

    with pytest.raises(RuntimeError, match="connect failed"):
        controller.connect()


def test_disconnect_clears_client_even_when_client_disconnect_fails():
    controller = OBSController(client_factory=FailingDisconnectClient)
    controller.connect()

    controller.disconnect()

    assert controller.client is None


def test_get_current_scene_returns_none_when_disconnected_or_client_fails():
    disconnected = OBSController(client_factory=FakeObsClient)
    assert disconnected.get_current_scene() is None

    failing = OBSController(client_factory=FailingCurrentSceneClient)
    failing.connect()
    assert failing.get_current_scene() is None


def test_set_scene_propagates_client_errors():
    controller = OBSController(client_factory=FailingSetSceneClient)
    controller.connect()

    with pytest.raises(RuntimeError, match="set failed"):
        controller.set_scene("Media")


def test_switch_to_media_scene_ignores_empty_scene():
    controller = OBSController(client_factory=FakeObsClient)
    controller.connect()

    controller.switch_to_media_scene("")

    assert controller.get_current_scene() == "Camera"
    assert controller.prev_scene is None


def test_switch_to_media_scene_without_current_scene_still_switches():
    controller = OBSController(client_factory=FailingCurrentSceneClient)
    controller.connect()

    controller.switch_to_media_scene("Media")

    assert controller.prev_scene is None
    assert controller.client.current_scene == "Media"


def test_revert_scene_noops_without_previous_scene():
    controller = OBSController(client_factory=FakeObsClient)
    controller.connect()

    controller.revert_scene()

    assert controller.get_current_scene() == "Camera"
