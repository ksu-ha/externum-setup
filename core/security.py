
import re


_PATTERNS = [
    (
        re.compile(
            r'''(?i)\b(password|passwd|pwd|passphrase|token|'''
            r'''access_token|refresh_token|secret|api[_-]?key|'''
            r'''client[_-]?secret)\b(\s*[:=]\s*)'''
            r'''("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|[^\s,;]+)'''
        ),
        1
    ),
    (
        re.compile(
            r'(?i)(authorization\s*:\s*bearer\s+)[^\s]+'
        ),
        2
    ),
    (
        re.compile(
            r'(?i)(-----BEGIN [A-Z ]*PRIVATE KEY-----)'
            r'.*?'
            r'(-----END [A-Z ]*PRIVATE KEY-----)',
            re.DOTALL
        ),
        3
    ),
]


def redact(value):
    text = str(value)

    for pattern, kind in _PATTERNS:
        if kind == 1:
            text = pattern.sub(
                lambda m: m.group(1) + m.group(2) + "[REDACTED]",
                text
            )
        elif kind == 2:
            text = pattern.sub(
                r'\1[REDACTED]',
                text
            )
        else:
            text = pattern.sub(
                r'\1\n[REDACTED PRIVATE KEY]\n\2',
                text
            )

    return text


def safe_dict(data):
    if not isinstance(data, dict):
        return redact(data)

    result = {}

    sensitive = {
        "password", "passwd", "pwd", "passphrase",
        "token", "access_token", "refresh_token",
        "secret", "api_key", "private_key",
        "client_secret", "authorization"
    }

    for key, value in data.items():
        if str(key).lower() in sensitive:
            result[key] = "[REDACTED]"
        elif isinstance(value, dict):
            result[key] = safe_dict(value)
        elif isinstance(value, list):
            result[key] = [
                safe_dict(item) if isinstance(item, dict)
                else redact(item)
                for item in value
            ]
        else:
            result[key] = redact(value)

    return result
