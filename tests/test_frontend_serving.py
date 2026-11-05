import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from web.server import create_app

@pytest.fixture
def client(tmp_path: Path):
    app = create_app(base_dir=tmp_path)
    return TestClient(app)

def test_frontend_static_serving(client: TestClient):
    res = client.get("/")
    assert res.status_code == 200
    assert "Landing Page Studio" in res.text
    assert "iframe" in res.text

    js_res = client.get("/app.js")
    assert js_res.status_code == 200
    assert "EventSource" in js_res.text or "createProject" in js_res.text


def test_studio_serves_modular_property_builder_hooks(client: TestClient):
    html_res = client.get("/")
    assert html_res.status_code == 200
    html = html_res.text
    assert 'id="section-picker-bar"' in html
    assert 'id="btn-new-project"' in html

    js_res = client.get("/app.js")
    assert js_res.status_code == 200
    js = js_res.text
    assert "section-picker-bar" in js
    assert "custom_properties" in js
    assert "version_form_inputs" in js
    assert "Cập nhật theo Properties" in js
