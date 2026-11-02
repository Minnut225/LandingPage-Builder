import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from web.server import create_app
from service import get_project_workspace

@pytest.fixture
def client(tmp_path: Path):
    app = create_app(base_dir=tmp_path)
    return TestClient(app)

def test_api_project_lifecycle(client: TestClient, tmp_path: Path):
    # Setup dummy project
    ws = get_project_workspace("test_proj", base_dir=tmp_path)
    ws.init_manifest("Build landing page", "html_css")
    ws.save_version(
        version_num=1,
        page_spec={"title": "Page 1"},
        design_spec={"theme": "light"},
        qa_report={"checks": [{"status": "pass", "name": "Responsive"}]},
        code="<html><body><h1>Hello World</h1></body></html>",
        code_filename="index.html"
    )
    ws.update_active_preview(1)

    # 1. Get project info
    res = client.get("/api/projects/test_proj")
    assert res.status_code == 200
    data = res.json()
    assert data["manifest"]["active_version"] == 1
    assert data["manifest"]["prompt"] == "Build landing page"
    assert data["qa_report"]["checks"][0]["name"] == "Responsive"

    # 2. Preview route
    prev_res = client.get("/preview/test_proj/index.html")
    assert prev_res.status_code == 200
    assert "<h1>Hello World</h1>" in prev_res.text

    # 3. Export zip
    zip_res = client.get("/api/projects/test_proj/export")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"
    zip_bytes = io.BytesIO(zip_res.content)
    with zipfile.ZipFile(zip_bytes) as z:
        assert "index.html" in z.namelist()
        assert "<h1>Hello World</h1>" in z.read("index.html").decode("utf-8")

    # 4. Approve project
    appr_res = client.post("/api/projects/test_proj/approve")
    assert appr_res.status_code == 200
    assert appr_res.json()["state"] == "approved"

    # 5. Rollback (save v2 first, then rollback to v1)
    ws.save_version(
        version_num=2,
        page_spec={"title": "Page 2"},
        design_spec={"theme": "dark"},
        qa_report={"checks": []},
        code="<html><body><h1>Version 2</h1></body></html>",
        code_filename="index.html"
    )
    ws.update_active_preview(2)
    assert ws.get_manifest()["active_version"] == 2

    rb_res = client.post("/api/projects/test_proj/rollback", json={"target_version": 1})
    assert rb_res.status_code == 200
    assert rb_res.json()["active_version"] == 1
    assert "Hello World" in client.get("/preview/test_proj/index.html").text

def test_preview_nonexistent_project_returns_404(client: TestClient):
    res = client.get("/preview/non_existent_project/index.html")
    assert res.status_code == 404
