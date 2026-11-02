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
