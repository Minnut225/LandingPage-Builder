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

def test_multi_user_e2e_workflow(client: TestClient, tmp_path: Path):
    # Setup Project A for User A
    ws_a = get_project_workspace("proj_user_a", base_dir=tmp_path)
    ws_a.init_manifest("Course landing page for AI", "html_css")
    ws_a.save_version(
        version_num=1,
        page_spec={"title": "Page A"},
        design_spec={"theme": "blue"},
        qa_report={"checks": [{"status": "pass", "name": "Layout"}]},
        code="<html><body>User A v1 Content</body></html>",
        code_filename="index.html"
    )
    ws_a.update_active_preview(1)

    # Setup Project B for User B simultaneously
    ws_b = get_project_workspace("proj_user_b", base_dir=tmp_path)
    ws_b.init_manifest("Coffee shop landing page", "html_css")
    ws_b.save_version(
        version_num=1,
        page_spec={"title": "Page B"},
        design_spec={"theme": "warm"},
        qa_report={"checks": [{"status": "pass", "name": "Menu"}]},
        code="<html><body>User B v1 Content</body></html>",
        code_filename="index.html"
    )
    ws_b.update_active_preview(1)

    # Verify Project A and B do not overwrite each other
    res_a = client.get("/api/projects/proj_user_a")
    res_b = client.get("/api/projects/proj_user_b")
    assert res_a.status_code == 200
    assert res_b.status_code == 200
    assert res_a.json()["manifest"]["prompt"] == "Course landing page for AI"
    assert res_b.json()["manifest"]["prompt"] == "Coffee shop landing page"

    # User A revisions to v2
    ws_a.save_version(
        version_num=2,
        page_spec={"title": "Page A v2"},
        design_spec={"theme": "blue"},
        qa_report={"checks": [{"status": "pass", "name": "Layout v2"}]},
        code="<html><body>User A v2 Revised</body></html>",
        code_filename="index.html"
    )
    ws_a.update_active_preview(2)

    # Check previews: User A shows v2, User B shows v1
    prev_a = client.get("/preview/proj_user_a/index.html")
    prev_b = client.get("/preview/proj_user_b/index.html")
    assert "User A v2 Revised" in prev_a.text
    assert "User B v1 Content" in prev_b.text

    # User A rolls back to v1
    rb_res = client.post("/api/projects/proj_user_a/rollback", json={"target_version": 1})
    assert rb_res.status_code == 200
    assert rb_res.json()["active_version"] == 1
    assert "User A v1 Content" in client.get("/preview/proj_user_a/index.html").text

    # User B approves project
    appr_b = client.post("/api/projects/proj_user_b/approve")
    assert appr_b.status_code == 200
    assert appr_b.json()["state"] == "approved"

    # Download exports for both
    zip_a = client.get("/api/projects/proj_user_a/export")
    zip_b = client.get("/api/projects/proj_user_b/export")

    with zipfile.ZipFile(io.BytesIO(zip_a.content)) as za:
        assert "User A v1 Content" in za.read("index.html").decode("utf-8")
    with zipfile.ZipFile(io.BytesIO(zip_b.content)) as zb:
        assert "User B v1 Content" in zb.read("index.html").decode("utf-8")
