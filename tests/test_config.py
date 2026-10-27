import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import shipright_config as cfg  # noqa: E402

YAML = """\
# comment
brain: ../brain            # trailing comment
product: my-app
red_zones:
  - "**/migrations/**"
  - '**/payment/**'
banks: [core, local/bank]
models:
  judge: inherit
  executor: sonnet
"""


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.proj = self.root / "proj"
        self.proj.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_unconfigured(self):
        self.assertEqual(cfg.load(self.proj).state, cfg.UNCONFIGURED)

    def test_ok(self):
        (self.root / "brain").mkdir()
        (self.proj / "shipright.yaml").write_text(YAML)
        r = cfg.load(self.proj)
        self.assertEqual(r.state, cfg.OK, r.reason)
        self.assertEqual(r.product, "my-app")
        self.assertEqual(r.red_zones, ["**/migrations/**", "**/payment/**"])
        self.assertEqual(r.banks, ["core", "local/bank"])
        self.assertEqual(r.models["executor"], "sonnet")
        self.assertTrue(os.path.isabs(r.brain))
        self.assertEqual(r.brain_raw, "../brain")
        self.assertEqual(r.gate, "commit")

    def test_gate_tiers(self):
        (self.root / "brain").mkdir()
        for value, state in (("file", cfg.OK), ("commit", cfg.OK), ("github", cfg.BROKEN), ("bogus", cfg.BROKEN)):
            (self.proj / "shipright.yaml").write_text(YAML + f"gate: {value}\n")
            r = cfg.load(self.proj)
            self.assertEqual(r.state, state, value)
        (self.proj / "shipright.yaml").write_text(YAML + "gate: github\n")
        self.assertIn("not implemented in v0.1", cfg.load(self.proj).reason)
        (self.proj / "shipright.yaml").write_text(YAML + "gate: bogus\n")
        self.assertIn("unknown gate tier", cfg.load(self.proj).reason)

    def test_broken_yaml(self):
        (self.proj / "shipright.yaml").write_text("brain ../brain\nproduct: x\n")
        r = cfg.load(self.proj)
        self.assertEqual(r.state, cfg.BROKEN)
        self.assertIn("parsed", r.reason)

    def test_missing_required_key(self):
        (self.root / "brain").mkdir()
        (self.proj / "shipright.yaml").write_text("brain: ../brain\n")
        r = cfg.load(self.proj)
        self.assertEqual(r.state, cfg.BROKEN)
        self.assertIn("product", r.reason)

    def test_missing_brain_dir(self):
        (self.proj / "shipright.yaml").write_text(YAML)
        r = cfg.load(self.proj)
        self.assertEqual(r.state, cfg.BROKEN)
        self.assertIn("brain directory does not exist", r.reason)

    def test_frontmatter_branches(self):
        fm = cfg.parse_frontmatter("---\nid: a\nbranches:\n  - feat/x\n  - fix/y\n---\nbody\n")
        self.assertEqual(fm["branches"], ["feat/x", "fix/y"])
        self.assertEqual(cfg.parse_frontmatter("no frontmatter"), {})


if __name__ == "__main__":
    unittest.main()
