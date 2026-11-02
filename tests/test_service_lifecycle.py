import unittest
from unittest.mock import patch, MagicMock
import shutil
from pathlib import Path
from service import LandingPageService, VersionResult

class TestServiceLifecycle(unittest.TestCase):
    def setUp(self):
        self.workspace = Path("output/test_service_workspace")
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
    def test_create_project_lifecycle(self, mock_qa, mock_frontend, mock_design, mock_plan):
        mock_plan.return_value = {"project_title": "Portfolio"}
        mock_design.return_value = {"visual_direction": "Minimal navy"}
        mock_frontend.return_value = "<!doctype html><html><body>Test</body></html>"
        mock_qa.return_value = {
            "summary": "Passed all tests",
            "checks": [{"id": "content", "status": "pass"}]
        }

        res = self.service.create_project("Portfolio brief", "html_css")
        self.assertEqual(res.version_num, 1)
        self.assertEqual(res.status, "awaiting_user_review")
        self.assertIsNotNone(self.service.get_active_preview_path())
        self.assertTrue(self.service.get_active_preview_path().exists())

    @patch("crew_builder.run_planning_stage")
    @patch("crew_builder.run_design_stage")
    @patch("crew_builder.run_frontend_stage")
    @patch("crew_builder.run_qa_stage")
    @patch("crew_builder.run_frontend_repair_stage")
    def test_strict_qa_gating_blocks_promotion_on_failure(
        self, mock_repair, mock_qa, mock_frontend, mock_design, mock_plan
    ):
        mock_plan.return_value = {"project_title": "Portfolio"}
        mock_design.return_value = {"visual_direction": "Minimal navy"}
        mock_frontend.return_value = "<!doctype html><html><body>Broken</body></html>"
        # Initial QA fails, repair QA also fails
        mock_qa.side_effect = [
            {"summary": "Defect", "checks": [{"id": "c1", "status": "fail"}]},
            {"summary": "Defect again", "checks": [{"id": "c1", "status": "fail"}]}
        ]
        mock_repair.return_value = "<!doctype html><html><body>Still Broken</body></html>"

        res = self.service.create_project("Portfolio brief", "html_css")
        self.assertEqual(res.status, "qa_failed")
        # Preview should not be promoted because candidate failed QA
        self.assertIsNone(self.service.get_active_preview_path())

    @patch("crew_builder.run_planning_stage")
    @patch("crew_builder.run_design_stage")
    @patch("crew_builder.run_frontend_stage")
    @patch("crew_builder.run_qa_stage")
    @patch("crew_builder.run_revision_plan_stage")
    @patch("crew_builder.run_frontend_revision_stage")
    def test_revision_and_rollback_flow(
        self, mock_front_rev, mock_plan_rev, mock_qa, mock_frontend, mock_design, mock_plan
    ):
        # 1. Create v1 successfully
        mock_plan.return_value = {"project_title": "Portfolio v1"}
        mock_design.return_value = {"visual_direction": "Navy"}
        mock_frontend.return_value = "<!doctype html><html><body>v1</body></html>"
        mock_qa.return_value = {"summary": "OK", "checks": [{"id": "c1", "status": "pass"}]}

        res_v1 = self.service.create_project("Portfolio brief", "html_css")
        self.assertEqual(res_v1.version_num, 1)

        # 2. Revise to v2
        mock_plan_rev.return_value = {
            "source_version": 1,
            "target_section_ids": ["hero"],
            "requested_changes": "Change title",
            "preserve": ["about"]
        }
        mock_front_rev.return_value = "<!doctype html><html><body>v2</body></html>"
        mock_qa.return_value = {"summary": "v2 OK", "checks": [{"id": "c1", "status": "pass"}]}

        res_v2 = self.service.revise_project("Change title to John Doe")
        self.assertEqual(res_v2.version_num, 2)
        preview_text = self.service.get_active_preview_path().read_text(encoding="utf-8")
        self.assertIn("v2", preview_text)

        # 3. Rollback to v1
        res_rb = self.service.rollback_to_version(1)
        self.assertEqual(res_rb.version_num, 1)
        preview_rb = self.service.get_active_preview_path().read_text(encoding="utf-8")
        self.assertIn("v1", preview_rb)

        # 4. User approval
        self.service.approve_current_version()
        manifest = self.service.get_manifest()
        self.assertEqual(manifest["state"], "approved")


if __name__ == "__main__":
    unittest.main()
