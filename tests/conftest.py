import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import config as config_module  # noqa: E402
from utils import db  # noqa: E402


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    """Point the config at a temporary copy of the example config."""
    path = tmp_path / "config.yaml"
    shutil.copy(ROOT / "data" / "config.yaml.example", path)
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)
    monkeypatch.setattr(config_module, "_cache", None)
    monkeypatch.setattr(config_module, "_cache_mtime", None)
    return path


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Use a fresh SQLite database for each test."""
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "rep.db"))
    db.init_db()
    return tmp_path / "rep.db"
