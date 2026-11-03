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
