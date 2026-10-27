import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parent.parent / "scripts" / "shipright_hooks.py")

YAML = """\
brain: ../brain
product: app
red_zones:
  - "**/migrations/**"
  - "**/payment/**"
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(os.path.realpath(self.tmp.name))
        self.proj = self.root / "proj"
        self.brain = self.root / "brain"
        self.data = self.root / "data"
        self.proj.mkdir()
        self.data.mkdir()
        self.sid = "sess1"

    def tearDown(self):
        self.tmp.cleanup()

    def configure(self):
        (self.brain / "products" / "app" / "decisions").mkdir(parents=True)
        (self.brain / "shared" / "decisions").mkdir(parents=True)
        (self.proj / "shipright.yaml").write_text(YAML)

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.proj, check=True, capture_output=True)

    def init_branch(self, branch):
        self.git("init", "-q")
        self.git("checkout", "-q", "-b", branch)

    def run_hook(self, event, payload=None, args=()):
        payload = dict(payload or {})
        payload.setdefault("session_id", self.sid)
        payload.setdefault("cwd", str(self.proj))
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(self.data), CLAUDE_PROJECT_DIR=str(self.proj),
                   SHIPRIGHT_NO_NOTIFY="1")
        env.pop("SHIPRIGHT_SESSION", None)
        p = subprocess.run([sys.executable, SCRIPT, event, *args], input=json.dumps(payload),
                           capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout) if p.stdout.strip() else None

    def prompt(self, text):
        return self.run_hook("user-prompt-submit", {"prompt": text})

    def pre(self, tool, tool_input=None, **extra):
        out = self.run_hook("pre-tool-use", {"tool_name": tool, "tool_input": tool_input or {}, **extra})
        return out["hookSpecificOutput"] if out else None


class BannerTests(Base):
    def test_unconfigured_banner_and_inert(self):
        out = self.prompt("hello")
        self.assertEqual(out["hookSpecificOutput"]["additionalContext"],
                         "Shipright: not configured for this project. Run /shipright:setup")
        self.assertIsNone(self.pre("Edit", {"file_path": str(self.proj / "migrations" / "a.py")}))
        self.assertIsNone(self.run_hook("stop"))

    def test_broken_banner_and_deny(self):
        (self.proj / "shipright.yaml").write_text(YAML)  # brain dir missing
        ctx = self.prompt("hi")["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(ctx.startswith("Shipright config is broken: brain directory does not exist"))
        self.assertTrue(ctx.endswith("Run /shipright:setup to repair."))
        for tool in ("Edit", "Write", "NotebookEdit"):
            r = self.pre(tool, {"file_path": "x.py"})
            self.assertEqual(r["permissionDecision"], "deny")
            self.assertIn("Run /shipright:setup to repair.", r["permissionDecisionReason"])
        self.assertIsNone(self.pre("Read", {"file_path": "x.py"}))

    def test_ok_banner(self):
        self.configure()
        ctx = self.prompt("hi")["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(ctx, "Shipright · mode: off · gate: on · brain: ../brain")


class RedZoneTests(Base):
    def setUp(self):
        super().setUp()
        self.configure()
        self.init_branch("feat/pay")
        self.target = str(self.proj / "app" / "payment" / "charge.py")

    def test_denied_without_consensus(self):
        r = self.pre("Write", {"file_path": self.target})
        self.assertEqual(r["permissionDecision"], "deny")
        reason = r["permissionDecisionReason"]
        self.assertEqual(len(reason.splitlines()), 4)
        self.assertIn("Gate tier: commit.", reason)
        self.assertIn("app/payment/charge.py is a red zone (**/payment/**)", reason)
        self.assertIn("branch feat/pay", reason)
        self.assertIn("/shipright:grill --override", reason)

    def test_relative_path_denied(self):
        r = self.pre("Edit", {"file_path": "db/migrations/001.sql"})
        self.assertEqual(r["permissionDecision"], "deny")

    def test_allowed_outside_zone(self):
        self.assertIsNone(self.pre("Write", {"file_path": str(self.proj / "src" / "a.py")}))

    def test_allowed_with_consensus_doc(self):
        (self.proj / "shipright.yaml").write_text(YAML + "gate: file\n")
        doc = self.brain / "products" / "app" / "decisions" / "pay.md"
        doc.write_text("---\nid: pay\nbranches:\n  - feat/pay\n---\nbody\n")
        self.assertIsNone(self.pre("Write", {"file_path": self.target}))

    def test_other_branch_doc_does_not_count(self):
        doc = self.brain / "shared" / "decisions" / "other.md"
        doc.write_text("---\nid: o\nbranches: [feat/other]\n---\n")
        self.assertEqual(self.pre("Write", {"file_path": self.target})["permissionDecision"], "deny")

    def test_no_git_repo_still_gated(self):
        import shutil
        shutil.rmtree(self.proj / ".git")
        r = self.pre("Write", {"file_path": self.target})
        self.assertEqual(r["permissionDecision"], "deny")
        self.assertIn("(no branch)", r["permissionDecisionReason"])


class CommitTierTests(Base):
    def setUp(self):
        super().setUp()
        self.configure()
        self.init_branch("feat/pay")
        self.target = str(self.proj / "app" / "payment" / "charge.py")
        self.doc = self.brain / "products" / "app" / "decisions" / "pay.md"
        self.doc.write_text("---\nid: pay\nbranches:\n  - feat/pay\n---\nbody\n")

    def bgit(self, *args):
        subprocess.run(["git", "-C", str(self.brain), *args], check=True, capture_output=True)

    def brain_init_commit(self, email="human@example.com"):
        self.bgit("init", "-q")
        self.bgit("add", ".")
        self.bgit("-c", "user.name=H", "-c", f"user.email={email}", "commit", "-q", "-m", "doc")

    def write_target(self):
        return self.pre("Write", {"file_path": self.target})

    def test_file_tier_allows_uncommitted(self):
        (self.proj / "shipright.yaml").write_text(YAML + "gate: file\n")
        self.assertIsNone(self.write_target())

    def test_default_denies_uncommitted_non_git_brain(self):
        r = self.write_target()
        self.assertEqual(r["permissionDecision"], "deny")
        self.assertIn("is not a git repository", r["permissionDecisionReason"])
        self.assertIn("set gate: file in shipright.yaml", r["permissionDecisionReason"])

    def test_denies_uncommitted_doc(self):
        self.bgit("init", "-q")
        r = self.write_target()
        self.assertEqual(r["permissionDecision"], "deny")
        self.assertIn("is not committed (gate tier: commit)", r["permissionDecisionReason"])

    def test_denies_dirty_doc(self):
        self.brain_init_commit()
        self.doc.write_text(self.doc.read_text() + "more\n")
        r = self.write_target()
        self.assertEqual(r["permissionDecision"], "deny")
        self.assertIn("is not committed", r["permissionDecisionReason"])

    def test_allows_committed_clean_doc(self):
        self.brain_init_commit()
        self.assertIsNone(self.write_target())

    def test_ai_git_email_denies(self):
        (self.proj / "shipright.yaml").write_text(YAML + "ai_git_email: AI@example.com\n")
        self.brain_init_commit(email="ai@example.com")
        r = self.write_target()
        self.assertEqual(r["permissionDecision"], "deny")
        self.assertIn("committed by the AI identity ai@example.com", r["permissionDecisionReason"])

    def test_ai_git_email_other_author_allows(self):
        (self.proj / "shipright.yaml").write_text(YAML + "ai_git_email: ai@example.com\n")
        self.brain_init_commit(email="human@example.com")
        self.assertIsNone(self.write_target())

    def test_bash_brain_commit_denied_in_commit_tier(self):
        r = self.pre("Bash", {"command": f"git -C {self.brain} commit -m x"})
        self.assertEqual(r["permissionDecision"], "deny")
        self.assertIn("committing to the brain is a human action", r["permissionDecisionReason"])

    def test_bash_other_commit_allowed(self):
        self.assertIsNone(self.pre("Bash", {"command": "git commit -m x"}))
        self.assertIsNone(self.pre("Bash", {"command": f"ls {self.brain}"}))

    def test_bash_brain_commit_allowed_in_file_tier(self):
        (self.proj / "shipright.yaml").write_text(YAML + "gate: file\n")
        self.assertIsNone(self.pre("Bash", {"command": f"git -C {self.brain} commit -m x"}))


class ModeTests(Base):
    def setUp(self):
        super().setUp()
        self.configure()

    def test_switch_via_prompt_text(self):
        ctx = self.prompt("/shipright:deep")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("mode: deep (0/10 lookups)", ctx)
        flag = json.loads((self.data / "modes" / "sess1.json").read_text())
        self.assertEqual(flag["mode"], "deep")
        ctx = self.prompt("/shipright:mode chat")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("mode: chat", ctx)
        ctx = self.prompt("/shipright:mode off")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("mode: off", ctx)
        self.assertFalse((self.data / "modes" / "sess1.json").exists())

    def test_chat_quota_exhausted(self):
        self.prompt("/shipright:chat")
        for _ in range(3):
            self.assertIsNone(self.pre("Read", {"file_path": "a"}))
        r = self.pre("Grep", {"pattern": "x"})
        self.assertEqual(r["permissionDecision"], "deny")
        self.assertIn("3/3", r["permissionDecisionReason"])
        self.assertIn("/shipright:deep", r["permissionDecisionReason"])
        self.prompt("next question")  # new turn resets the count
        self.assertIsNone(self.pre("Read", {"file_path": "a"}))

    def test_chat_blocks_agent_and_edits(self):
        self.prompt("/shipright:chat")
        self.assertEqual(self.pre("Agent", {"subagent_type": "scout"})["permissionDecision"], "deny")
        self.assertEqual(self.pre("Edit", {"file_path": "a.py"})["permissionDecision"], "deny")
        self.assertIsNone(self.pre("Skill", {}))

    def test_deep_agents(self):
        self.prompt("/shipright:deep")
        self.assertIsNone(self.pre("Agent", {"subagent_type": "scout"}))
        self.assertIsNone(self.pre("Agent", {"subagent_type": "shipright:scout"}))
        r = self.pre("Agent", {"subagent_type": "executor"})
        self.assertEqual(r["permissionDecision"], "deny")
        self.assertIn("read-only", r["permissionDecisionReason"])
        self.assertEqual(self.pre("Write", {"file_path": "a.py"})["permissionDecision"], "deny")

    def test_delegate_edit_asks_and_lookup_quota(self):
        self.prompt("/shipright:delegate")
        self.assertEqual(self.pre("Edit", {"file_path": "a.py"})["permissionDecision"], "ask")
        for _ in range(5):
            self.assertIsNone(self.pre("Bash", {"command": "ls"}))
        r = self.pre("Bash", {"command": "ls"})
        self.assertEqual(r["permissionDecision"], "deny")
        self.assertIn("scout", r["permissionDecisionReason"])
        self.assertIsNone(self.pre("Agent", {"subagent_type": "executor"}))

    def test_subagent_calls_not_counted(self):
        self.prompt("/shipright:chat")
        for _ in range(5):
            self.assertIsNone(self.pre("Read", {}, agent_id="a1", agent_type="scout"))
        self.assertEqual(self.pre("Edit", {"file_path": "a"}, agent_id="a1")["permissionDecision"], "deny")

    def test_cli_set_status_clear(self):
        self.prompt("hello")  # records current session
        self.run_hook("session-start")
        self.run_hook("x", args=())
        p = subprocess.run([sys.executable, SCRIPT, "set", "deep"], capture_output=True, text=True,
                           env=dict(os.environ, CLAUDE_PLUGIN_DATA=str(self.data)))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads((self.data / "modes" / "sess1.json").read_text())["mode"], "deep")
        p = subprocess.run([sys.executable, SCRIPT, "clear"], capture_output=True, text=True,
                           env=dict(os.environ, CLAUDE_PLUGIN_DATA=str(self.data)))
        self.assertFalse((self.data / "modes" / "sess1.json").exists())

    def test_chat_word_limit_on_stop(self):
        self.prompt("/shipright:chat 5")
        tr = self.root / "t.jsonl"
        text = "one two three four five six seven"
        tr.write_text(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}))
        out = self.run_hook("stop", {"transcript_path": str(tr)})
        self.assertEqual(out["decision"], "block")
        self.assertIsNone(self.run_hook("stop", {"transcript_path": str(tr), "stop_hook_active": True}))


class WorkflowTests(Base):
    def setUp(self):
        super().setUp()
        self.configure()

    def test_missing_model_denied(self):
        script = "await agent('a', {model: 'haiku'});\nawait agent('b', {label: 'x'});"
        r = self.pre("Workflow", {"script": script})
        self.assertEqual(r["permissionDecision"], "deny")
        self.assertIn("Every agent() in a Workflow must set model. Found 1 without", r["permissionDecisionReason"])

    def test_strong_model_asks_and_good_passes(self):
        r = self.pre("Workflow", {"script": "agent('a', {model: 'opus'})"})
        self.assertEqual(r["permissionDecision"], "ask")
        self.assertIsNone(self.pre("Workflow", {"script": "agent('a', {model: 'sonnet'})"}))


class SubagentMonitorTests(Base):
    def setUp(self):
        super().setUp()
        self.configure()

    def test_alert_then_single_block(self):
        self.prompt("/shipright:delegate")
        for i in range(5):
            self.run_hook("subagent-start", {"agent_id": f"a{i}", "agent_type": "scout"})
        out = self.run_hook("stop")
        self.assertEqual(out["decision"], "block")
        self.assertIn("Subagent status:", out["reason"])
        self.assertIsNone(self.run_hook("stop"))  # alerts consumed
        self.run_hook("subagent-stop", {"agent_id": "a0", "agent_type": "scout"})


if __name__ == "__main__":
    unittest.main()
