import unittest
from crew_builder import _load_skill

class TestSkills(unittest.TestCase):
    def test_load_all_required_skills(self):
        for name in ("planner", "design", "frontend", "qa", "revision"):
            content = _load_skill(name)
            self.assertTrue(len(content) > 50, f"Skill {name} content too short")

    def test_skills_mention_formats_and_rules(self):
        frontend_skill = _load_skill("frontend")
        self.assertIn("React", frontend_skill)
        self.assertIn("HTML", frontend_skill)

        qa_skill = _load_skill("qa")
        self.assertIn("pass", qa_skill)
        self.assertIn("TypeScript", qa_skill)

        revision_skill = _load_skill("revision")
        self.assertIn("revision_request", revision_skill)


if __name__ == "__main__":
    unittest.main()
