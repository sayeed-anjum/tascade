from fastapi.testclient import TestClient

from app.main import app


def _create_project(client: TestClient, name: str) -> dict:
    response = client.post("/v1/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()


class TestListProjects:
    def test_list_projects_returns_empty_list_when_no_projects(self):
        client = TestClient(app)
        response = client.get("/v1/projects")
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []

    def test_list_projects_returns_all_projects(self):
        client = TestClient(app)
        proj_a = _create_project(client, "Project Alpha")
        proj_b = _create_project(client, "Project Beta")

        response = client.get("/v1/projects")
        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 2
        returned_ids = {item["id"] for item in body["items"]}
        assert returned_ids == {proj_a["id"], proj_b["id"]}

    def test_list_projects_items_contain_required_fields(self):
        client = TestClient(app)
        _create_project(client, "Field Check Project")

        response = client.get("/v1/projects")
        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert "id" in item
        assert item["name"] == "Field Check Project"
        assert "status" in item
        assert "created_at" in item

    def test_list_projects_ordered_by_created_at_desc(self):
        client = TestClient(app)
        proj_a = _create_project(client, "First Project")
        proj_b = _create_project(client, "Second Project")

        response = client.get("/v1/projects")
        assert response.status_code == 200
        body = response.json()
        returned_ids = [item["id"] for item in body["items"]]
        # Most recently created first
        assert returned_ids == [proj_b["id"], proj_a["id"]]


class TestGetProject:
    def test_get_project_returns_project_detail(self):
        client = TestClient(app)
        created = _create_project(client, "Detail Project")
        project_id = created["id"]

        response = client.get(f"/v1/projects/{project_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == project_id
        assert body["name"] == "Detail Project"
        assert body["status"] == "active"
        assert "created_at" in body
        assert "updated_at" in body

    def test_get_project_returns_404_for_nonexistent_id(self):
        client = TestClient(app)
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = client.get(f"/v1/projects/{fake_id}")
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "PROJECT_NOT_FOUND"

    def test_get_project_returns_404_for_invalid_id(self):
        client = TestClient(app)

        response = client.get("/v1/projects/not-a-valid-uuid")
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "PROJECT_NOT_FOUND"
