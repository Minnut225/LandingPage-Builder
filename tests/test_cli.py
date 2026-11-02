import unittest
from main import format_qa_report, parse_user_command

class TestCLI(unittest.TestCase):
    def test_format_qa_report(self):
        report = {
            "summary": "Verified successfully",
            "checks": [
                {"id": "content", "name": "Content Check", "status": "pass", "details": "All sections present"},
                {"id": "contrast", "name": "Accessibility Contrast", "status": "fail", "details": "Low contrast on button"}
            ]
        }
        formatted = format_qa_report(report)
        self.assertIn("[PASS]", formatted)
        self.assertIn("[FAIL]", formatted)
        self.assertIn("Content Check", formatted)
        self.assertIn("Low contrast on button", formatted)

    def test_parse_user_command(self):
        self.assertEqual(parse_user_command("approve"), ("approve", None))
        self.assertEqual(parse_user_command("approved"), ("approve", None))
        self.assertEqual(parse_user_command("yes"), ("approve", None))
        self.assertEqual(parse_user_command("rollback 2"), ("rollback", 2))
        self.assertEqual(parse_user_command("q"), ("quit", None))
        self.assertEqual(parse_user_command("quit"), ("quit", None))
        self.assertEqual(parse_user_command("Change button to violet"), ("feedback", "Change button to violet"))

    def test_preview_page_react_starts_server(self):
        from unittest.mock import MagicMock, patch
        from pathlib import Path
        from main import preview_page

        mock_server = MagicMock()
        mock_server.start_server.return_value = "http://localhost:5173"
        dummy_path = Path("output/site/src/App.tsx")

        with patch.object(Path, "exists", return_value=True), patch("webbrowser.open") as mock_open:
            preview_page(dummy_path, "react_ts", server_manager=mock_server)
            mock_server.start_server.assert_called_once()
            mock_open.assert_called_once_with("http://localhost:5173")


if __name__ == "__main__":
    unittest.main()
