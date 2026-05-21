from src.ui.config_store import load_obs_config, save_obs_config


def test_load_obs_config_returns_none_when_file_is_missing(tmp_path):
    assert load_obs_config(tmp_path / "missing.json") is None


def test_save_and_load_obs_config_round_trip(tmp_path):
    path = tmp_path / "config.json"
    config = {
        "obs_host": "localhost",
        "obs_port": "4455",
        "obs_password": "secret",
        "threshold": "15",
        "baseline_rms": 2.5,
        "baseline_rms_delta": "7",
    }

    saved_path = save_obs_config(config, path)

    assert saved_path == path
    assert load_obs_config(path) == config
