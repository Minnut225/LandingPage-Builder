import unittest
from unittest.mock import patch
import shutil
import json
from pathlib import Path
from service import LandingPageService

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.workspace = Path("output/test_integration_workspace")
        if self.workspace.exists():
            shutil.rmtree(self.workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.service = LandingPageService(self.workspace)

    def tearDown(self):
        if self.workspace.exists():
            shutil.rmtree(self.workspace)

    @patch("crew_builder.run_planning_stage")
    @patch("crew_builder.run_design_stage")
    @patch("crew_builder.run_frontend_stage")
    @patch("crew_builder.run_qa_stage")
    @patch("crew_builder.run_revision_plan_stage")
    @patch("crew_builder.run_frontend_revision_stage")
    def test_end_to_end_html_flow(
        self, mock_front_rev, mock_plan_rev, mock_qa, mock_frontend, mock_design, mock_plan
    ):
        # 1. Initial creation (v1)
        mock_plan.return_value = {
            "project_title": "AI Engineer Portfolio",
            "audience": "Tech Recruiters",
            "primary_goal": "Showcase LLM projects",
            "sections": [{"id": "hero", "type": "Hero", "purpose": "Intro", "content_requirements": "Title & CTA"}]
        }
        mock_design.return_value = {
            "visual_direction": "Minimal dark navy",
            "color_tokens": {"primary": "#0f172a", "accent": "#8b5cf6"}
        }
        mock_frontend.return_value = "<!doctype html><html><head><title>v1</title></head><body><h1>AI Engineer</h1></body></html>"
        mock_qa.return_value = {
            "summary": "All checks passed",
            "checks": [
                {"id": "content", "status": "pass", "details": "All sections included"},
                {"id": "accessibility", "status": "pass", "details": "Semantic markup valid"}
            ]
        }

        v1_res = self.service.create_project("Build AI Engineer page", "html_css")
        self.assertEqual(v1_res.version_num, 1)
        self.assertEqual(v1_res.status, "awaiting_user_review")

        # Verify artifacts in v1 folder
        v1_dir = self.workspace / "versions" / "v1"
        self.assertTrue((v1_dir / "page_spec.json").exists())
        self.assertTrue((v1_dir / "design_spec.json").exists())
        self.assertTrue((v1_dir / "code" / "index.html").exists())
        self.assertTrue((v1_dir / "qa_report.json").exists())
        self.assertTrue((v1_dir / "metadata.json").exists())

        # Verify active preview
        active_preview = self.service.get_active_preview_path()
        self.assertIsNotNone(active_preview)
        self.assertIn("AI Engineer", active_preview.read_text(encoding="utf-8"))

        # 2. Revision (v2)
        mock_plan_rev.return_value = {
            "source_version": 1,
            "target_section_ids": ["hero"],
            "requested_changes": "Change title to Senior AI Engineer",
            "preserve": ["contact"]
        }
        mock_front_rev.return_value = "<!doctype html><html><head><title>v2</title></head><body><h1>Senior AI Engineer</h1></body></html>"
        mock_qa.return_value = {
            "summary": "Revision passed QA",
            "checks": [{"id": "content", "status": "pass"}]
        }

        v2_res = self.service.revise_project("Upgrade title to Senior AI Engineer")
        self.assertEqual(v2_res.version_num, 2)
        self.assertIn("Senior AI Engineer", active_preview.read_text(encoding="utf-8"))

        # 3. Rollback to v1
        rb_res = self.service.rollback_to_version(1)
        self.assertEqual(rb_res.version_num, 1)
        self.assertIn("<h1>AI Engineer</h1>", active_preview.read_text(encoding="utf-8"))

        # 4. Final approval
        self.service.approve_current_version()
        manifest = self.service.get_manifest()
        self.assertEqual(manifest["state"], "approved")
        self.assertEqual(manifest["active_version"], 1)

    @patch("crew_builder.run_planning_stage")
    @patch("crew_builder.run_design_stage")
    @patch("crew_builder.run_frontend_stage")
    @patch("crew_builder.run_qa_stage")
    def test_end_to_end_react_flow(
        self, mock_qa, mock_frontend, mock_design, mock_plan
    ):
        mock_plan.return_value = {"project_title": "React Portfolio"}
        mock_design.return_value = {"visual_direction": "Clean modern"}
        mock_frontend.return_value = (
            "import React from 'react';\n"
            "export default function App() {\n"
            "  return <div className='p-8'><h1>React Portfolio</h1></div>;\n"
            "}"
        )
        mock_qa.return_value = {
            "summary": "React TSX passed QA",
            "checks": [{"id": "react_syntax", "status": "pass"}]
        }

        res = self.service.create_project("Build React page", "react_ts")
        self.assertEqual(res.version_num, 1)

        v1_code = self.workspace / "versions" / "v1" / "code" / "App.tsx"
        self.assertTrue(v1_code.exists())
        self.assertIn("export default function App", v1_code.read_text(encoding="utf-8"))

        preview_file = self.service.get_active_preview_path()
        self.assertEqual(preview_file.name, "App.tsx")


if __name__ == "__main__":
    unittest.main()
