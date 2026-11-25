import os
import shutil
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="marketmind-tests-"))
os.environ["DATA_DIR"] = str(_TMP)


@pytest.fixture(autouse=True)
def clean_data():
    for item in _TMP.iterdir():
        item.unlink() if item.is_file() else shutil.rmtree(item)
    yield


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_TMP, ignore_errors=True)
