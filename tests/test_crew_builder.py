import unittest
from crew_builder import _extract_json, _extract_code

class TestCrewBuilder(unittest.TestCase):
    def test_extract_json_clean(self):
        text = '{"audience": "Engineers", "goal": "Showcase portfolio"}'
        data = _extract_json(text)
        self.assertEqual(data["audience"], "Engineers")

    def test_extract_json_with_backticks(self):
        text = '```json\n{"audience": "Engineers"}\n```'
        data = _extract_json(text)
        self.assertEqual(data["audience"], "Engineers")

    def test_extract_code_html(self):
        text = '<!doctype html><html><head><title>Test</title></head><body>OK</body></html>'
        code = _extract_code(text, "html_css")
        self.assertIn("<!doctype html>", code)

    def test_extract_code_react(self):
        text = '```tsx\nexport default function App() { return <h1>Hello</h1>; }\n```'
        code = _extract_code(text, "react_ts")
        self.assertIn("export default function App", code)


if __name__ == "__main__":
    unittest.main()
