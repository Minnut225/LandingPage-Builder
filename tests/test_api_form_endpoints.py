from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from web.server import create_app


@pytest.fixture
def client(tmp_path: Path):
    app = create_app(base_dir=tmp_path)
    return TestClient(app)


def test_get_templates_endpoint(client: TestClient):
    res = client.get("/api/templates")
    assert res.status_code == 200
    data = res.json()
    assert "templates" in data
    assert "styles" in data
    assert "palettes" in data
    assert "personal_portfolio" in data["templates"]


def test_preview_prompt_endpoint(client: TestClient):
    payload = {
        "template_id": "personal_portfolio",
        "form_data": {
            "full_name": "Nguyễn Văn A",
            "title": "Senior AI Engineer",
            "skills": "Python, PyTorch, LangChain",
        },
        "style": "modern_clean",
        "color_palette": {"name": "Tech Blue", "primary": "#2563EB"},
    }
    res = client.post("/api/prompt/preview", json=payload)
    assert res.status_code == 200
    assert "Nguyễn Văn A" in res.json()["prompt"]
    assert "Senior AI Engineer" in res.json()["prompt"]


def test_create_project_with_form_payload(client: TestClient):
    payload = {
        "template_id": "saas_product",
        "form_data": {"product_name": "FastSaaS", "cta_text": "Thử ngay"},
        "style": "tech_dark",
        "color_palette": {"name": "Tech Blue", "primary": "#2563EB"},
        "output_format": "html_css",
    }
    res = client.post("/api/projects", json=payload)
    assert res.status_code == 200
    assert "project_id" in res.json()


def test_create_project_backward_compatibility(client: TestClient):
    res = client.post("/api/projects", json={"prompt": "Custom prompt directly"})
    assert res.status_code == 200
    assert "project_id" in res.json()


from service import get_project_workspace


def _seed_project_v1(tmp_path: Path, project_id: str, form_input: dict):
    ws = get_project_workspace(project_id, base_dir=tmp_path)
    ws.init_manifest("Initial prompt", "html_css", form_input=form_input)
    ws.save_version_artifacts(
        version_num=1,
        page_spec={"project_title": "Demo"},
        design_spec={"visual_direction": "Clean"},
        code="<!doctype html><html><body>v1</body></html>",
        qa_report={"checks": [{"id": "c1", "status": "pass"}]},
        metadata={"status": "passed", "form_input": form_input},
    )
    ws.promote_preview(1)
    return ws


def test_revise_endpoint_rejects_empty_and_noop_property_updates(client: TestClient, tmp_path: Path):
    v1_input = {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "color_palette": {"id": "tech_blue", "name": "Tech Blue", "primary": "#2563EB"},
        "form_data": {
            "sections": {
                "about_me": {"enabled": True, "values": {"full_name": "Minh", "title": "AI Dev", "bio": "Hello"}}
            }
        },
    }
    _seed_project_v1(tmp_path, "lp_rev_test", v1_input)

    # Empty feedback and no form_data -> 400
    res_empty = client.post("/api/projects/lp_rev_test/revise", json={"feedback": "   "})
    assert res_empty.status_code == 400

    # Identical form_data and blank feedback -> 400 immediately
    res_noop = client.post(
        "/api/projects/lp_rev_test/revise",
        json={
            "template_id": "personal_portfolio",
            "style": "modern_clean",
            "color_palette": {"id": "tech_blue", "name": "Tech Blue", "primary": "#2563EB"},
            "form_data": v1_input["form_data"],
            "feedback": "",
        },
    )
    assert res_noop.status_code == 400
    assert "thay đổi" in res_noop.json()["detail"].lower()


def test_revise_endpoint_enqueues_valid_property_update_and_get_project_returns_version_inputs(
    client: TestClient, tmp_path: Path
):
    v1_input = {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "color_palette": {"id": "tech_blue", "name": "Tech Blue", "primary": "#2563EB"},
        "form_data": {
            "sections": {
                "about_me": {"enabled": True, "values": {"full_name": "Minh", "title": "AI Dev", "bio": "Hello"}}
            }
        },
    }
    ws = _seed_project_v1(tmp_path, "lp_ver_inputs", v1_input)

    # Valid property update should enqueue with 200
    v2_input = {
        **v1_input,
        "form_data": {
            "sections": {
                "about_me": {"enabled": True, "values": {"full_name": "Minh", "title": "Senior AI Dev", "bio": "Hello"}}
            }
        },
    }
    rev_ok = client.post(
        "/api/projects/lp_ver_inputs/revise",
        json={
            "template_id": v2_input["template_id"],
            "style": v2_input["style"],
            "color_palette": v2_input["color_palette"],
            "form_data": v2_input["form_data"],
            "feedback": "",
        },
    )
    assert rev_ok.status_code == 200
    assert rev_ok.json()["status"] == "queued"

    # Add v2 artifact manually to verify version_form_inputs & rollback via API
    ws.save_version_artifacts(
        version_num=2,
        page_spec={},
        design_spec={},
        code="<!doctype html><html><body>v2</body></html>",
        qa_report={"checks": [{"id": "c1", "status": "pass"}]},
        metadata={"status": "passed", "form_input": v2_input},
    )
    ws.promote_preview(2)

    proj_res = client.get("/api/projects/lp_ver_inputs")
    assert proj_res.status_code == 200
    body = proj_res.json()
    assert body["version_form_inputs"]["1"] == v1_input
    assert body["version_form_inputs"]["2"] == v2_input
    assert body["manifest"]["form_input"] == v2_input

    # Rollback via API restores manifest["form_input"] to v1_input
    rb_res = client.post("/api/projects/lp_ver_inputs/rollback", json={"target_version": 1})
    assert rb_res.status_code == 200
    assert rb_res.json()["form_input"] == v1_input
