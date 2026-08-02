from app.core.monitoring import _before_send
from app.core.observability import redact_fields


def test_structured_field_allowlist_redacts_secrets_and_raw_input():
    safe = redact_fields(
        {
            "request_id": "req_1",
            "origin": "ATL",
            "authorization": "Bearer secret",
            "cookie": "session=secret",
            "database_url": "postgresql://secret",
            "query": "raw user input",
            "passport": "secret",
        }
    )
    assert safe == {"request_id": "req_1", "origin": "ATL"}


def test_sentry_filter_removes_request_payload_headers_and_cookies():
    event = {
        "request": {
            "headers": {"authorization": "secret"},
            "cookies": {"session": "secret"},
            "data": {"passport": "secret"},
            "query_string": "token=secret",
            "method": "POST",
        }
    }
    filtered = _before_send(event, {})
    assert filtered == {"request": {"method": "POST"}}
