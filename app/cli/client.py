"""HTTP transport for the ``tascade`` CLI.

The transport is injectable so the CLI can be exercised end to end in tests
against a FastAPI ``TestClient`` without a live server.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from app.cli.config import Config

Transport = Callable[[str, str, dict[str, str], bytes | None], tuple[int, bytes]]

DEFAULT_TIMEOUT_SECONDS = 30


class ApiError(Exception):
    """A non-2xx response from the Tascade API."""

    def __init__(self, status: int, code: str, message: str, body: Any = None) -> None:
        super().__init__(f"{code}: {message}")
        self.status = status
        self.code = code
        self.message = message
        self.body = body


class TransportError(Exception):
    """The request never reached the API (DNS, refused connection, timeout)."""


def _encode_query(query: dict[str, Any]) -> str:
    pairs: list[tuple[str, str]] = []
    for key, value in query.items():
        if value is None:
            continue
        if isinstance(value, bool):
            pairs.append((key, "true" if value else "false"))
        elif isinstance(value, (list, tuple)):
            pairs.extend((key, str(item)) for item in value)
        else:
            pairs.append((key, str(value)))
    return urllib.parse.urlencode(pairs)


def urllib_transport(
    method: str, url: str, headers: dict[str, str], body: bytes | None
) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        # A 4xx/5xx is a real answer from the API; hand it back for decoding.
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        raise TransportError(f"could not reach {url}: {exc.reason}") from exc


class ApiClient:
    def __init__(self, config: Config, transport: Transport | None = None) -> None:
        self._config = config
        self._transport = transport or urllib_transport

    def request(
        self,
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        url = self._config.url + path
        encoded_query = _encode_query(query or {})
        if encoded_query:
            url = f"{url}?{encoded_query}"

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        payload: bytes | None = None
        if body is not None:
            pruned = {k: v for k, v in body.items() if v is not None}
            payload = json.dumps(pruned).encode("utf-8")

        status, raw = self._transport(method, url, headers, payload)
        decoded = _decode(raw)
        if status >= 400:
            raise ApiError(status, *_error_fields(status, decoded), body=decoded)
        return decoded


def _decode(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw.decode("utf-8", errors="replace")


def _error_fields(status: int, decoded: Any) -> tuple[str, str]:
    """Pull ``code`` and ``message`` out of the API's error envelope."""
    envelope = decoded.get("error") if isinstance(decoded, dict) else None
    if isinstance(envelope, dict):
        return str(envelope.get("code", f"HTTP_{status}")), str(envelope.get("message", ""))
    if isinstance(decoded, dict) and "detail" in decoded:
        return f"HTTP_{status}", json.dumps(decoded["detail"])
    return f"HTTP_{status}", "" if decoded is None else str(decoded)
