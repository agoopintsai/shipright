import datetime
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "brain_lint.py"


def doc(id_, **over):
    fm = {"id": id_, "memory": "episodic", "source": '["test"]', "status": "active",
          "last_verified": datetime.date.today().isoformat()}
    fm.update(over)
    lines = [f"{k}: {v}" for k, v in fm.items() if v is not None]
    return "---\n" + "\n".join(lines) + "\n---\n\n# Doc\n"


def write(root, rel, text):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def make_brain(root, direction=True):
    if direction:
        write(root, "products/app/DIRECTION.md", "# Direction\n")
    write(root, "products/app/decisions/a.md", doc("app/decisions/a", relates_to="[app/decisions/b]"))
    write(root, "products/app/decisions/b.md", doc("app/decisions/b", relates_to="[app/decisions/a]"))


def run(root, *extra):
    r = subprocess.run([sys.executable, str(SCRIPT), str(root), *extra],
                       capture_output=True, text=True)
    return r.returncode, r.stdout


class BrainLintTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean(self):
        make_brain(self.root)
        code, out = run(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("0 errors, 0 warnings", out)

    def test_missing_field(self):
        make_brain(self.root)
        write(self.root, "products/app/decisions/a.md",
              doc("app/decisions/a", relates_to="[app/decisions/b]", source=None))
        code, out = run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("ERROR: missing required field 'source'", out)

    def test_dangling_link(self):
        make_brain(self.root)
        write(self.root, "products/app/decisions/a.md",
              doc("app/decisions/a", relates_to="[app/decisions/b, nope]"))
        code, out = run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("dangling relates_to target 'nope'", out)

    def test_bad_enum_and_duplicate(self):
        make_brain(self.root)
        write(self.root, "shared/decisions/c.md", doc("app/decisions/a", memory="dreamy"))
        code, out = run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("bad memory", out)
        self.assertIn("duplicate id", out)

    def test_no_direction_warns(self):
        make_brain(self.root, direction=False)
        code, out = run(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("WARN: product has no DIRECTION.md", out)

    def test_stale_warns(self):
        make_brain(self.root)
        old = (datetime.date.today() - datetime.timedelta(days=400)).isoformat()
        write(self.root, "products/app/decisions/a.md",
              doc("app/decisions/a", relates_to="[app/decisions/b]", last_verified=old))
        code, out = run(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("WARN: last_verified", out)

    def test_orphan_warns_and_graph(self):
        make_brain(self.root)
        write(self.root, "shared/decisions/lonely.md", doc("shared/lonely"))
        out_json = str(Path(self.root) / "g.json")
        code, out = run(self.root, "--graph", out_json)
        self.assertEqual(code, 0, out)
        self.assertIn("orphan doc", out)
        self.assertTrue(Path(out_json).is_file())

    def test_block_list_and_superseded(self):
        make_brain(self.root)
        write(self.root, "products/app/decisions/old.md",
              doc("app/decisions/old", status="superseded-by:app/decisions/a"))
        write(self.root, "products/app/decisions/new.md",
              "---\nid: app/decisions/new\nmemory: semantic\nsource:\n  - x\nstatus: active\n"
              f"last_verified: {datetime.date.today().isoformat()}\nsupersedes:\n  - app/decisions/old\n---\n")
        code, out = run(self.root)
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
