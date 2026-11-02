import unittest
import json
import shutil
from pathlib import Path
from service import (
    extract_json_payload,
    extract_code_payload,
    is_qa_passing,
    WorkspaceManager,
)

class TestServiceCore(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("output/test_workspace")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_extract_json_with_markdown_fences(self):
        raw = "Here is the spec:\n```json\n{\"project_title\": \"Demo\"}\n```\nHope it helps!"
        res = extract_json_payload(raw)
        self.assertEqual(res["project_title"], "Demo")

    def test_extract_json_without_fences(self):
        raw = '{"project_title": "Plain JSON", "sections": []}'
        res = extract_json_payload(raw)
        self.assertEqual(res["project_title"], "Plain JSON")

    def test_extract_html_code_payload(self):
        raw = "```html\n<!doctype html><html><body><h1>Hello</h1></body></html>\n```"
        res = extract_code_payload(raw, "html_css")
        self.assertTrue(res.startswith("<!doctype html>"))
        self.assertTrue(res.endswith("</html>"))

    def test_extract_react_code_payload(self):
        raw = "```tsx\nimport React from 'react';\nexport default function App() { return <div>Demo</div>; }\n```"
        res = extract_code_payload(raw, "react_ts")
        self.assertIn("export default function App", res)

    def test_is_qa_passing_all_pass(self):
        report = {
            "summary": "OK",
            "checks": [
                {"id": "c1", "status": "pass"},
                {"id": "c2", "status": "pass"},
                {"id": "c3", "status": "not_run"}
            ]
        }
        self.assertTrue(is_qa_passing(report))

    def test_is_qa_passing_with_fail(self):
        report = {
            "summary": "Defects found",
            "checks": [
                {"id": "c1", "status": "pass"},
                {"id": "c2", "status": "fail"}
            ]
        }
        self.assertFalse(is_qa_passing(report))

    def test_workspace_manifest_and_versioning(self):
        wm = WorkspaceManager(self.test_dir)
        manifest = wm.init_manifest("Build landing page", "html_css")
        self.assertEqual(manifest["prompt"], "Build landing page")
        self.assertEqual(manifest["output_format"], "html_css")

        v_dir = wm.create_version_dir(1)
        self.assertTrue(v_dir.exists())

        wm.save_version_artifacts(
            version_num=1,
            page_spec={"title": "Test"},
            design_spec={"palette": []},
            code="<!doctype html><html><body>Test</body></html>",
            qa_report={"checks": [{"id": "c1", "status": "pass"}]},
            metadata={"status": "passed"}
        )
        self.assertTrue((v_dir / "page_spec.json").exists())
        self.assertTrue((v_dir / "code" / "index.html").exists())
        self.assertTrue((v_dir / "qa_report.json").exists())

        # Test preview promotion
        wm.promote_preview(1)
        preview_file = self.test_dir / "index.html"
        self.assertTrue(preview_file.exists())
        self.assertIn("Test", preview_file.read_text(encoding="utf-8"))

        # Verify manifest active_version update
        updated_manifest = wm.get_manifest()
        self.assertEqual(updated_manifest["active_version"], 1)

    def test_scaffold_react_project(self):
        wm = WorkspaceManager(self.test_dir)
        wm.scaffold_react_project(self.test_dir)
        self.assertTrue((self.test_dir / "package.json").exists())
        self.assertTrue((self.test_dir / "vite.config.ts").exists())
        self.assertTrue((self.test_dir / "tailwind.config.js").exists())
        self.assertTrue((self.test_dir / "postcss.config.js").exists())
        self.assertTrue((self.test_dir / "index.html").exists())
        self.assertTrue((self.test_dir / "src" / "main.tsx").exists())
        self.assertTrue((self.test_dir / "src" / "index.css").exists())

    def test_promote_preview_react_scaffolding(self):
        wm = WorkspaceManager(self.test_dir)
        wm.init_manifest("Build react landing", "react_ts")
        wm.create_version_dir(1)
        wm.save_version_artifacts(
            version_num=1,
            page_spec={"title": "React Landing"},
            design_spec={"palette": []},
            code="export default function App() { return <div>React App</div>; }",
            qa_report={"checks": [{"id": "c1", "status": "pass"}]},
            metadata={"status": "passed"}
        )
        preview_path = wm.promote_preview(1)
        self.assertIsNotNone(preview_path)
        self.assertTrue((self.test_dir / "src" / "App.tsx").exists())
        self.assertTrue((self.test_dir / "App.tsx").exists())
        self.assertIn("React App", (self.test_dir / "src" / "App.tsx").read_text(encoding="utf-8"))
        self.assertIn("React App", (self.test_dir / "App.tsx").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
