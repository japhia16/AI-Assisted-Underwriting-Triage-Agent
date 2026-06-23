from unittest.mock import MagicMock, patch

import requests
from streamlit.runtime import Runtime
from streamlit.runtime.caching.storage.dummy_cache_storage import (
    MemoryCacheStorageManager,
)
from streamlit.runtime.media_file_manager import MediaFileManager
from streamlit.runtime.memory_media_file_storage import MemoryMediaFileStorage
from streamlit.testing.local_script_runner import LocalScriptRunner


def _run_ui_script():
    mock_runtime = MagicMock(spec=Runtime)
    mock_runtime.media_file_mgr = MediaFileManager(MemoryMediaFileStorage("/mock/media"))
    mock_runtime.cache_storage_manager = MemoryCacheStorageManager()
    Runtime._instance = mock_runtime

    try:
        runner = LocalScriptRunner("ui.py")
        return runner.run()
    finally:
        Runtime._instance = None


def _sidebar_alert_texts(tree):
    texts = []
    for elt in tree.sidebar:
        if getattr(elt, "type", None) == "alert":
            alert = elt.proto.alert
            if hasattr(alert, "body"):
                texts.append(alert.body)
            elif hasattr(alert, "text"):
                texts.append(alert.text)
            else:
                texts.append(str(alert))
    return texts


@patch("requests.get")
def test_ui_health_check_online(mock_get):
    """CI test: the UI opens and shows backend health online."""
    mock_get.return_value.status_code = 200

    tree = _run_ui_script()

    assert not tree.get("exception"), "The UI crashed during startup."
    sidebar_messages = _sidebar_alert_texts(tree)
    assert any("🟢 API Gateway: ONLINE" in msg for msg in sidebar_messages)


@patch("requests.get")
def test_ui_health_check_offline(mock_get):
    """CI test: the UI opens and shows backend health offline."""
    mock_get.side_effect = requests.exceptions.ConnectionError

    tree = _run_ui_script()

    assert not tree.get("exception"), "The UI crashed when handling an offline backend."
    sidebar_messages = _sidebar_alert_texts(tree)
    assert any("🔴 API Gateway: OFFLINE" in msg for msg in sidebar_messages)
