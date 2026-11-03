from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from web.server import create_app
from service import get_project_workspace


@pytest.fixture
def client(tmp_path: Path):
    app = create_app(base_dir=tmp_path)
    return TestClient(app)


def test_full_form_e2e_pipeline(client: TestClient, tmp_path: Path):
    # 1. Fetch templates
    res = client.get("/api/templates")
    assert res.status_code == 200
    templates = res.json()["templates"]
    assert "course_workshop" in templates

    # 2. Preview prompt
    preview_res = client.post(
        "/api/prompt/preview",
        json={
            "template_id": "course_workshop",
            "form_data": {
                "course_title": "Khóa học AI Agent thực chiến",
                "instructor": "Kỹ sư AI Senior",
                "benefits": "Tự xây dựng multi-agent\nDeploy production",
                "tuition": "Miễn phí",
            },
            "style": "modern_clean",
        },
    )
    assert preview_res.status_code == 200
    prompt_text = preview_res.json()["prompt"]
    assert "Khóa học AI Agent thực chiến" in prompt_text
    assert "Kỹ sư AI Senior" in prompt_text

    # 3. Create dummy project workspace with manifest
    ws = get_project_workspace("proj_form_test", base_dir=tmp_path)
    manifest = ws.init_manifest(prompt_text, "html_css")
    manifest["form_input"] = {
        "template_id": "course_workshop",
        "form_data": {"course_title": "Khóa học AI Agent thực chiến"},
    }
    ws.save_manifest(manifest)

    # 4. Check project endpoint returns manifest with form_input
    proj_res = client.get("/api/projects/proj_form_test")
    assert proj_res.status_code == 200
    assert proj_res.json()["manifest"]["form_input"]["template_id"] == "course_workshop"
