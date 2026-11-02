import unittest
import json
import shutil
from pathlib import Path
from service import (
    is_qa_passing,
    extract_code_payload,
    LandingPageService,
    MAX_HTML_CHARS,
)

class TestReviewFixes(unittest.TestCase):
    def setUp(self):
        self.workspace = Path("output/test_fixes_workspace")
        if self.workspace.exists():
            shutil.rmtree(self.workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.service = LandingPageService(self.workspace)

    def tearDown(self):
        if self.workspace.exists():
            shutil.rmtree(self.workspace)

    def test_is_qa_passing_case_insensitivity_and_empty_list(self):
        # Uppercase FAIL should fail
        self.assertFalse(is_qa_passing({"checks": [{"id": "c1", "status": "FAIL"}]}))
        # Titlecase Failed should fail
        self.assertFalse(is_qa_passing({"checks": [{"id": "c1", "status": "Failed"}]}))
        # Empty checks list should fail
        self.assertFalse(is_qa_passing({"checks": []}))
        # Missing checks key should fail
        self.assertFalse(is_qa_passing({}))
        # Valid pass should pass
        self.assertTrue(is_qa_passing({"checks": [{"id": "c1", "status": "pass"}]}))

    def test_extract_react_code_multi_block_and_language_tags(self):
        # Multi-block: bash fence before tsx fence
        multi_block_text = (
            "Here is how to install dependencies:\n"
            "```bash\n"
            "npm install lucide-react\n"
            "```\n"
            "And here is the component:\n"
            "```tsx\n"
            "import React from 'react';\n"
            "export default function App() { return <div>AI Portfolio</div>; }\n"
            "```\n"
        )
        code = extract_code_payload(multi_block_text, "react_ts")
        self.assertIn("export default function App", code)
        self.assertNotIn("npm install", code)

        # ts tag should not leak into code
        ts_tagged_text = "```ts\nimport React from 'react';\nexport default function App() {}\n```"
        code_ts = extract_code_payload(ts_tagged_text, "react_ts")
        self.assertFalse(code_ts.startswith("ts\n"))
        self.assertTrue(code_ts.startswith("import React"))

        # Size limit guard for react_ts
        huge_text = "```tsx\nexport default function App() {}\n" + ("x" * (MAX_HTML_CHARS + 10)) + "\n```"
        with self.assertRaises(ValueError):
            extract_code_payload(huge_text, "react_ts")

    def test_rollback_guards_against_qa_failed_versions(self):
        wm = self.service.wm
        wm.init_manifest("Prompt", "html_css")
        wm.save_version_artifacts(
            version_num=1,
            page_spec={},
            design_spec={},
            code="<!doctype html><html><body>v1</body></html>",
            qa_report={"checks": [{"id": "c", "status": "fail"}]},
            metadata={"status": "qa_failed"}
        )
        # Attempting rollback to a failed version should raise ValueError
        with self.assertRaises(ValueError) as ctx:
            self.service.rollback_to_version(1)
        self.assertIn("failed QA", str(ctx.exception))

    @unittest.mock.patch("crew_builder.run_revision_plan_stage")
    @unittest.mock.patch("crew_builder.run_frontend_revision_stage")
    @unittest.mock.patch("crew_builder.run_qa_stage")
    def test_revise_from_failed_initial_candidate(self, mock_qa, mock_front, mock_rev_plan):
        mock_rev_plan.return_value = {"source_version": 1, "target_section_ids": [], "requested_changes": "Fix", "preserve": []}
        mock_front.return_value = "<!doctype html><html><body>Candidate v2</body></html>"
        mock_qa.return_value = {"checks": [{"id": "c", "status": "pass"}]}

        # When v1 failed QA, manifest has active_version = None, but versions = [1]
        wm = self.service.wm
        manifest = wm.init_manifest("Prompt", "html_css")
        manifest["versions"] = [1]
        manifest["active_version"] = None
        wm.save_manifest(manifest)
        v1_dir = wm.create_version_dir(1)
        (v1_dir / "code" / "index.html").write_text("<!doctype html><html><body>Candidate</body></html>", encoding="utf-8")
        (v1_dir / "page_spec.json").write_text("{}", encoding="utf-8")
        (v1_dir / "design_spec.json").write_text("{}", encoding="utf-8")

        res = self.service.revise_project("Feedback")
        self.assertEqual(res.version_num, 2)
        self.assertEqual(res.status, "awaiting_user_review")


if __name__ == "__main__":
    unittest.main()
