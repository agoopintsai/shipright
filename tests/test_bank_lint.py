import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINT = ROOT / "scripts" / "bank_lint.py"

GOOD = """---
id: gatekeeping-09-sample
category: gatekeeping
must_answer: false
added: 2026-10-23
---

## Question

Is this a sample?

## Why it matters

Because tests need one.
"""


def run(folder):
    r = subprocess.run([sys.executable, str(LINT), str(folder)], capture_output=True, text=True)
    return r.returncode, r.stdout


class BankLintTest(unittest.TestCase):
    def case(self, name, text):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        (Path(d.name) / name).write_text(text, encoding="utf-8")
        return run(d.name)

    def test_core_bank_passes(self):
        code, out = run(ROOT / "banks" / "core")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(list((ROOT / "banks" / "core").glob("*.md"))), 15)

    def test_good_file_passes(self):
        code, out = self.case("gatekeeping-09-sample.md", GOOD)
        self.assertEqual(code, 0, out)

    def test_no_frontmatter(self):
        code, out = self.case("gatekeeping-09-sample.md", "## Question\nx\n")
        self.assertEqual(code, 1)
        self.assertIn("frontmatter", out)

    def test_missing_field(self):
        code, out = self.case("gatekeeping-09-sample.md", GOOD.replace("added: 2026-10-23\n", ""))
        self.assertEqual(code, 1)
        self.assertIn("missing field 'added'", out)

    def test_id_mismatch(self):
        code, out = self.case("gatekeeping-09-sample.md", GOOD.replace("id: gatekeeping-09-sample", "id: other"))
        self.assertEqual(code, 1)
        self.assertIn("does not match file name", out)

    def test_bad_category(self):
        code, out = self.case("gatekeeping-09-sample.md", GOOD.replace("category: gatekeeping", "category: misc"))
        self.assertEqual(code, 1)
        self.assertIn("invalid category", out)

    def test_bad_must_answer(self):
        code, out = self.case("gatekeeping-09-sample.md", GOOD.replace("must_answer: false", "must_answer: maybe"))
        self.assertEqual(code, 1)
        self.assertIn("must_answer", out)

    def test_bad_date(self):
        code, out = self.case("gatekeeping-09-sample.md", GOOD.replace("2026-10-23", "23/10/2026"))
        self.assertEqual(code, 1)
        self.assertIn("YYYY-MM-DD", out)

    def test_missing_section(self):
        code, out = self.case("gatekeeping-09-sample.md", GOOD.replace("## Why it matters", "## Reason"))
        self.assertEqual(code, 1)
        self.assertIn("missing section '## Why it matters'", out)

    def test_bad_file_name(self):
        code, out = self.case("Sample.md", GOOD.replace("id: gatekeeping-09-sample", "id: Sample"))
        self.assertEqual(code, 1)
        self.assertIn("does not match <category>", out)

    def test_empty_folder(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        code, _ = run(d.name)
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
