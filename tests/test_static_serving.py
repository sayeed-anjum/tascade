"""Tests for static file serving and SPA fallback routing.

Verifies that:
- API endpoints (/v1/*, /health) are unaffected by the static mount
- Static assets are served correctly from web/dist/
- SPA fallback returns index.html for unknown client-side routes
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestApiRoutesUnaffected:
    """API routes must continue to work with static mount active."""

    def test_health_endpoint_still_works(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_v1_projects_still_works(self):
        response = client.get("/v1/projects")
        assert response.status_code == 200
        body = response.json()
        assert "items" in body

    def test_v1_project_not_found_still_returns_json(self):
        response = client.get("/v1/projects/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "PROJECT_NOT_FOUND"


class TestStaticAssets:
    """Hashed static assets under /assets/ must be served."""

    def test_css_asset_returns_200(self):
        response = client.get("/assets/index-DpCr0HGY.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]

    def test_js_asset_returns_200(self):
        response = client.get("/assets/index-DqvTHtkR.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]

    def test_missing_asset_returns_404(self):
        response = client.get("/assets/nonexistent-abc123.js")
        assert response.status_code == 404

    def test_vite_svg_returns_200(self):
        response = client.get("/vite.svg")
        assert response.status_code == 200
        assert "svg" in response.headers["content-type"]


class TestSpaFallback:
    """Non-API, non-asset paths must serve index.html for client-side routing."""

    def test_root_serves_index_html(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<div id=\"root\"></div>" in response.text

    def test_client_route_serves_index_html(self):
        response = client.get("/projects")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<div id=\"root\"></div>" in response.text

    def test_nested_client_route_serves_index_html(self):
        response = client.get("/projects/abc/tasks/def")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<div id=\"root\"></div>" in response.text

    def test_unknown_path_serves_index_html(self):
        response = client.get("/some/unknown/deep/path")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<div id=\"root\"></div>" in response.text
