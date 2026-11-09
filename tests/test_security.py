
from core.security import redact, safe_dict


def test_password_redaction():
    text = "password=SuperSecret123"

    result = redact(text)

    assert "SuperSecret123" not in result
    assert "[REDACTED]" in result


def test_token_redaction():
    text = "access_token: abc123"

    result = redact(text)

    assert "abc123" not in result


def test_bearer_redaction():
    text = "Authorization: Bearer abc123"

    result = redact(text)

    assert "abc123" not in result


def test_safe_dict():
    data = {
        "username": "admin",
        "password": "secret",
        "network": {
            "token": "abc"
        }
    }

    result = safe_dict(data)

    assert result["username"] == "admin"
    assert result["password"] == "[REDACTED]"
    assert result["network"]["token"] == "[REDACTED]"
