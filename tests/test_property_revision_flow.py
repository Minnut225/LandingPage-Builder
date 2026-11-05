from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

import crew_builder
from service import LandingPageService


def _make_portfolio_form_input(project_names: list[str], skills_enabled: bool = False) -> dict:
    return {
        "template_id": "personal_portfolio",
        "style": "modern_clean",
        "color_palette": {"id": "tech_blue", "name": "Tech Blue", "primary": "#2563EB"},
        "form_data": {
            "sections": {
                "about_me": {
                    "enabled": True,
                    "values": {"full_name": "Nguyễn Minh", "title": "AI Engineer", "bio": "Build AI Agents"},
                },
                "projects": {
                    "enabled": True,
                    "items": [
                        {"id": f"proj_{idx}", "values": {"name": name, "role": "Dev", "tech_stack": ["Python"]}}
                        for idx, name in enumerate(project_names, start=1)
                    ],
                },
                "skills": {"enabled": skills_enabled, "tags": ["Python", "FastAPI"] if skills_enabled else []},
            }
        },
    }


@patch("crew_builder.run_planning_stage")
@patch("crew_builder.run_design_stage")
@patch("crew_builder.run_frontend_stage")
@patch("crew_builder.run_qa_stage")
@patch("crew_builder.run_revision_plan_stage")
@patch("crew_builder.run_frontend_revision_stage")
def test_property_revision_updates_version_metadata_and_rollback_restores_form_input(
    mock_front_rev, mock_rev_plan, mock_qa, mock_front, mock_design, mock_plan, tmp_path: Path
):
    service = LandingPageService(tmp_path / "proj_1")
    v1_input = _make_portfolio_form_input(["AI Doc Assistant"])

    mock_plan.return_value = {"project_title": "Minh Portfolio"}
    mock_design.return_value = {"visual_direction": "Clean"}
    mock_front.return_value = "<!doctype html><html><body>v1 AI Doc Assistant</body></html>"
    mock_qa.return_value = {"summary": "OK", "checks": [{"id": "content", "status": "pass"}]}

    res1 = service.create_project("Initial brief", "html_css", form_input=v1_input)
    assert res1.version_num == 1
    assert service.get_manifest()["form_input"] == v1_input

    # Update properties in v2: delete AI Doc Assistant, add LandingPage Builder + enable skills
    v2_input = _make_portfolio_form_input(["LandingPage Builder"], skills_enabled=True)
    mock_rev_plan.return_value = {
        "source_version": 1,
        "target_section_ids": ["projects", "skills"],
        "requested_changes": "Update projects and add skills",
        "preserve": ["about_me"],
    }
    mock_front_rev.return_value = "<!doctype html><html><body>v2 LandingPage Builder</body></html>"
    mock_qa.return_value = {"summary": "v2 OK", "checks": [{"id": "content", "status": "pass"}]}

    res2 = service.revise_project(feedback="", form_input=v2_input)
    assert res2.version_num == 2
    assert service.get_manifest()["form_input"] == v2_input

    # Verify synthesized diff was passed to revision planner and revision_request was passed to QA
    rev_feedback_arg = mock_rev_plan.call_args.kwargs["feedback"]
    assert "AI Doc Assistant" in rev_feedback_arg
    assert "LandingPage Builder" in rev_feedback_arg
    assert mock_qa.call_args.kwargs.get("revision_request") == mock_rev_plan.return_value

    # Rollback to v1 must restore manifest["form_input"] back to v1_input
    service.rollback_to_version(1)
    assert service.get_manifest()["active_version"] == 1
    assert service.get_manifest()["form_input"] == v1_input


@patch("crew_builder.run_planning_stage")
@patch("crew_builder.run_design_stage")
@patch("crew_builder.run_frontend_stage")
@patch("crew_builder.run_qa_stage")
@patch("crew_builder.run_revision_plan_stage")
@patch("crew_builder.run_frontend_revision_stage")
@patch("crew_builder.run_frontend_repair_stage")
def test_failed_qa_on_property_revision_preserves_v1_manifest_form_input(
    mock_repair, mock_front_rev, mock_rev_plan, mock_qa, mock_front, mock_design, mock_plan, tmp_path: Path
):
    service = LandingPageService(tmp_path / "proj_qa_fail")
    v1_input = _make_portfolio_form_input(["Project One"])
    v2_input = _make_portfolio_form_input(["Project One", "Project Two"])

    mock_plan.return_value = {"project_title": "Portfolio"}
    mock_design.return_value = {"visual_direction": "Clean"}
    mock_front.return_value = "<!doctype html><html><body>v1</body></html>"
    mock_qa.return_value = {"summary": "OK", "checks": [{"id": "c1", "status": "pass"}]}
    service.create_project("Brief", "html_css", form_input=v1_input)

    # Now v2 fails QA on both initial and repair attempts
    mock_rev_plan.return_value = {"source_version": 1, "requested_changes": "Add Project Two"}
    mock_front_rev.return_value = "<!doctype html><html><body>broken v2</body></html>"
    mock_repair.return_value = "<!doctype html><html><body>still broken v2</body></html>"
    mock_qa.side_effect = [
        {"summary": "Fail 1", "checks": [{"id": "c1", "status": "fail"}]},
        {"summary": "Fail 2", "checks": [{"id": "c1", "status": "fail"}]},
    ]

    res2 = service.revise_project(feedback="", form_input=v2_input)
    assert res2.status == "qa_failed"
    assert service.get_manifest()["active_version"] == 1
    assert service.get_manifest()["form_input"] == v1_input  # Must NOT be overwritten!


def test_noop_property_revision_raises_value_error_without_calling_agents(tmp_path: Path):
    service = LandingPageService(tmp_path / "proj_noop")
    v1_input = _make_portfolio_form_input(["Project One"])
    wm = service.wm
    manifest = wm.init_manifest("Brief", "html_css", form_input=v1_input)
    wm.save_version_artifacts(
        version_num=1,
        page_spec={},
        design_spec={},
        code="<!doctype html><html><body>v1</body></html>",
        qa_report={"checks": [{"id": "c1", "status": "pass"}]},
        metadata={"status": "passed", "form_input": v1_input},
    )
    wm.promote_preview(1)

    with pytest.raises(ValueError, match="Không có thay đổi"):
        service.revise_project(feedback="   ", form_input=v1_input)


@patch("crew_builder._make_agents")
@patch("crew_builder.Task")
@patch("crew_builder.Crew")
def test_run_qa_stage_injects_revision_request_context(mock_crew_cls, mock_task_cls, mock_make_agents):
    mock_make_agents.return_value = {"qa": MagicMock()}
    mock_crew_inst = MagicMock()
    mock_crew_inst.kickoff.return_value = '{"summary": "OK", "checks": [{"id": "content", "status": "pass"}]}'
    mock_crew_cls.return_value = mock_crew_inst

    rev_req = {"requested_changes": "Remove AI Doc Assistant, add LandingPage Builder"}
    crew_builder.run_qa_stage(
        "<!doctype html><html><body>Code</body></html>",
        page_spec={"project_title": "Old Spec"},
        design_spec={},
        output_format="html_css",
        revision_request=rev_req,
    )
    task_desc = mock_task_cls.call_args.kwargs["description"]
    assert "APPLIED REVISION REQUEST" in task_desc
    assert "Remove AI Doc Assistant" in task_desc
