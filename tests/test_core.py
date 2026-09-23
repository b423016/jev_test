import unittest

from app.actions import build_actions
from app.explain import _ground
from app.hashing import hashes_match, sha256_hex
from app.paragraphs import split_paragraphs


class HashTests(unittest.TestCase):
    def test_match(self):
        data = b"Employee hereby assigns all inventions."
        self.assertTrue(hashes_match(sha256_hex(data), data))

    def test_tamper(self):
        data = b"Employee hereby assigns all inventions."
        self.assertFalse(hashes_match(sha256_hex(data), data + b" "))

    def test_odd_length_rejected(self):
        self.assertFalse(hashes_match("abc", b"hi"))


class ParagraphTests(unittest.TestCase):
    def test_joins_short_heading(self):
        text = "Pay\n\nThe salary is $10 and may be changed by the company."
        parts = split_paragraphs(text)
        self.assertEqual(len(parts), 1)
        self.assertIn("salary", parts[0])


class GroundTests(unittest.TestCase):
    def test_keeps_amount_present_in_the_paragraph(self):
        paragraph = "Bonus target is $15,000 and is discretionary."
        self.assertEqual(_ground(paragraph, "$15,000"), "$15,000")

    def test_drops_amount_the_model_invented(self):
        paragraph = "The bonus is discretionary."
        self.assertEqual(_ground(paragraph, "$15,000"), "")


class RouteTests(unittest.TestCase):
    def test_rejects_a_hash_that_does_not_match_the_text(self):
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        response = client.post(
            "/scans",
            data={
                "document_type": "offer",
                "sha256": "ab" * 32,
                "text": "The company may change compensation at any time.",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("compensation", response.text)


class ActionTests(unittest.TestCase):
    def test_reminder_requires_a_date_from_a_finding(self):
        findings = [
            {"question": "Does the vest start on June 1, 2026?", "date": "", "text": "x", "explanation": ""},
            {"question": "", "date": "June 1, 2026", "text": "Vests June 1, 2026.", "explanation": "A date."},
        ]
        draft, reminder = build_actions("offer", findings)
        self.assertIn("Does the vest", draft)
        self.assertEqual(reminder["date"], "June 1, 2026")


if __name__ == "__main__":
    unittest.main()
