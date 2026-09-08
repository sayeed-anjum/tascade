"""The CLI's HTTP client and human-readable rendering."""

import json

import pytest

from app.cli.client import ApiClient, ApiError
from app.cli.config import Config
from app.cli.render import render


def _config(api_key: str | None = None) -> Config:
    return Config(url="http://host:1", api_key=api_key)


class TestApiClient:
    def test_sends_bearer_and_json_body(self):
        seen: dict = {}

        def transport(method, url, headers, body):
            seen.update(method=method, url=url, headers=headers, body=body)
            return 200, b'{"ok": true}'

        client = ApiClient(_config("k"), transport=transport)
        assert client.request("POST", "/v1/x", body={"a": 1, "b": None}) == {"ok": True}
        assert seen["method"] == "POST"
        assert seen["url"] == "http://host:1/v1/x"
        assert seen["headers"]["Authorization"] == "Bearer k"
        assert seen["headers"]["Content-Type"] == "application/json"
        assert json.loads(seen["body"]) == {"a": 1}

    def test_omits_auth_header_when_no_key(self):
        def transport(method, url, headers, body):
            assert "Authorization" not in headers
            return 200, b"{}"

        ApiClient(_config(), transport=transport).request("GET", "/v1/x")

    def test_sends_no_body_for_get(self):
        def transport(method, url, headers, body):
            assert body is None
            return 200, b"{}"

        ApiClient(_config(), transport=transport).request("GET", "/v1/x")

    def test_builds_query_string_and_drops_none(self):
        seen: dict = {}

        def transport(method, url, headers, body):
            seen["url"] = url
            return 200, b"{}"

        ApiClient(_config(), transport=transport).request(
            "GET", "/v1/x", query={"project_id": "p1", "state": None, "limit": 5}
        )
        assert seen["url"] == "http://host:1/v1/x?project_id=p1&limit=5"

    def test_serialises_booleans_as_lowercase_in_query(self):
        seen: dict = {}

        def transport(method, url, headers, body):
            seen["url"] = url
            return 200, b"{}"

        ApiClient(_config(), transport=transport).request(
            "GET", "/v1/x", query={"include_completed": False}
        )
        assert seen["url"].endswith("include_completed=false")

    def test_raises_api_error_with_code_from_error_envelope(self):
        def transport(*_):
            return 409, b'{"error": {"code": "LEASE_EXISTS", "message": "busy"}}'

        with pytest.raises(ApiError) as exc:
            ApiClient(_config(), transport=transport).request("POST", "/v1/x")
        assert exc.value.status == 409
        assert exc.value.code == "LEASE_EXISTS"
        assert exc.value.message == "busy"

    def test_raises_api_error_for_unstructured_failure(self):
        def transport(*_):
            return 500, b"boom"

        with pytest.raises(ApiError) as exc:
            ApiClient(_config(), transport=transport).request("GET", "/v1/x")
        assert exc.value.status == 500
        assert exc.value.code == "HTTP_500"

    def test_handles_empty_success_body(self):
        def transport(*_):
            return 204, b""

        assert ApiClient(_config(), transport=transport).request("POST", "/v1/x") is None


class TestRender:
    def test_renders_items_list_one_per_line(self):
        out = render(
            {
                "items": [
                    {"short_id": "P1.M1.T1", "title": "CLI", "state": "ready"},
                    {"short_id": "P1.M1.T2", "title": "Brief", "state": "blocked"},
                ]
            }
        )
        lines = out.splitlines()
        assert len(lines) == 2
        assert "P1.M1.T1" in lines[0] and "CLI" in lines[0] and "ready" in lines[0]
        assert "P1.M1.T2" in lines[1]

    def test_renders_empty_items_as_a_notice(self):
        assert render({"items": []}) == "(no items)"

    def test_renders_mapping_as_aligned_key_values(self):
        out = render({"id": "abc", "state": "ready"})
        assert "id:" in out and "abc" in out
        assert "state:" in out and "ready" in out

    def test_renders_nested_values_as_compact_json(self):
        out = render({"work_spec": {"objective": "o"}})
        assert '{"objective": "o"}' in out

    def test_renders_plain_scalar(self):
        assert render("hello") == "hello"
