import contextvars
import logging
from typing import Optional

# Context variable to hold the request id per context
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)


def set_request_id(req_id: Optional[str]) -> None:
    if req_id is None:
        # Clear by setting to None
        request_id_var.set(None)
    else:
        request_id_var.set(req_id)


def get_request_id() -> Optional[str]:
    return request_id_var.get()


class RequestIdFilter(logging.Filter):
    """Logging filter that injects request_id into LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            rid = get_request_id()
        except Exception:
            rid = None
        # Attach attribute so formatters can use it
        record.request_id = rid or "-"
        return True
