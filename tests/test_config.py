import src.config as config


def test_detection_thresholds_are_positive():
    assert config.RMS_THRESHOLD > 0
    assert config.BASELINE_RMS_DELTA > 0
    assert config.PRESENCE_FRAMES_REQUIRED > 0
    assert config.ABSENCE_FRAMES_REQUIRED > 0
    assert config.POLL_INTERVAL > 0


def test_obs_defaults_are_present():
    assert config.OBS_HOST
    assert isinstance(config.OBS_PORT, int)
    assert 0 < config.OBS_PORT < 65536
    assert isinstance(config.OBS_PASSWORD, str)


def test_scene_defaults_are_present():
    assert "default" in config.SCENES
    assert "media" in config.SCENES
    assert config.MEDIA_SCENE_NAME
