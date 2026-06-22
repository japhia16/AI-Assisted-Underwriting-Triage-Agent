import logging
from fastapi.testclient import TestClient
from src.main import app


def test_request_id_appears_in_logs(caplog):
    client = TestClient(app)
    with caplog.at_level(logging.INFO):
        resp = client.post("/extract", json={"text": "Need a quote for my warehouse."})
    request_id_header = resp.headers.get("X-Request-ID")
    assert request_id_header is not None
    # Check whether any captured log record actually carries the same request_id
    found = any(getattr(r, "request_id", None) == request_id_header for r in caplog.records)
    assert found, "request_id from the response header was not found on any captured log record"
    request_id_header = resp.headers.get("X-Request-ID")
    assert request_id_header is not None
    # Check whether any captured log record actually carries the same request_id
    found = any(getattr(r, "request_id", None) == request_id_header for r in caplog.records)
    assert found, "request_id from the response header was not found on any captured log record"
