from pathlib import Path
from unittest.mock import MagicMock, patch
from service import LandingPageService, get_project_workspace

def test_create_project_emits_progress_events(tmp_path: Path):
    ws = get_project_workspace("test_proj_events", base_dir=tmp_path)
    service = LandingPageService(ws.root_dir)

    events = []
    def callback(stage: str, data: dict):
        events.append((stage, data))

    with patch("crew_builder.run_planning_stage") as mock_planner, \
         patch("crew_builder.run_design_stage") as mock_designer, \
         patch("crew_builder.run_frontend_stage") as mock_frontend, \
         patch("crew_builder.run_qa_stage") as mock_qa:
        
        mock_planner.return_value = {"title": "Test"}
        mock_designer.return_value = {"theme": "light"}
        mock_frontend.return_value = "<!doctype html><html><body>Test</body></html>"
        mock_qa.return_value = {"summary": "Passed", "checks": [{"status": "pass"}]}

        res = service.create_project("Build landing page", progress_callback=callback)
        assert res.status == "awaiting_user_review"

    stages = [stage for stage, _ in events]
    assert "planning" in stages
    assert "designing" in stages
    assert "generating" in stages
    assert "qa_review" in stages
    assert "completed" in stages
