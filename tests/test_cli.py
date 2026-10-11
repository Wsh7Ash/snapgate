import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from snapgate.cli import main

PY = sys.executable.replace("\\", "/")
PROJECT_ROOT = Path(__file__).resolve().parents[1]

BASE = """
[run]
snapshot_dir = "snapshots"

[[case]]
name = "hello"
command = ["%(py)s", "-c", "print('hello world')"]

[[case]]
name = "noisy"
command = ["%(py)s", "-c", "import datetime,uuid;print(datetime.datetime(2026,1,2,3,4,5).isoformat(), uuid.uuid4())"]
""" % {"py": PY}


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.cfg = self.dir / "snapgate.toml"
        self.cfg.write_text(BASE, encoding="utf-8")

    def run_cli(self, *argv: str):
        import contextlib
        import io

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_full_cycle_exit_codes(self) -> None:
        code, out, _ = self.run_cli("run", "-c", str(self.cfg))
        self.assertEqual(code, 1)
        self.assertIn("missing", out)

        code, _, _ = self.run_cli("run", "-c", str(self.cfg), "--update")
        self.assertEqual(code, 0)

        code, out, _ = self.run_cli("run", "-c", str(self.cfg))
        self.assertEqual(code, 0)
        self.assertIn("2 pass", out)

    def test_json_report(self) -> None:
        self.run_cli("run", "-c", str(self.cfg), "--update")
        code, out, _ = self.run_cli("run", "-c", str(self.cfg), "--json")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual({p["name"] for p in payload}, {"hello", "noisy"})
        self.assertTrue(all(p["status"] == "pass" for p in payload))

    def test_json_reports_failure(self) -> None:
        self.run_cli("run", "-c", str(self.cfg), "--update")
        self.cfg.write_text(BASE.replace("hello world", "goodbye world"), encoding="utf-8")
        code, out, _ = self.run_cli("run", "-c", str(self.cfg), "--json")
        self.assertEqual(code, 1)
        payload = json.loads(out)
        hello = next(p for p in payload if p["name"] == "hello")
        self.assertEqual(hello["status"], "fail")
        self.assertIn("differs from snapshot", hello["reason"])

    def test_only_filter_and_no_match(self) -> None:
        self.run_cli("run", "-c", str(self.cfg), "--update")
        code, out, _ = self.run_cli("run", "-c", str(self.cfg), "--only", "hello")
        self.assertEqual(code, 0)
        self.assertIn("1 pass", out)

        code, _, err = self.run_cli("run", "-c", str(self.cfg), "--only", "zzz")
        self.assertEqual(code, 2)
        self.assertIn("no cases match", err)

    def test_config_error_is_exit_2(self) -> None:
        code, _, err = self.run_cli("run", "-c", str(self.dir / "absent.toml"))
        self.assertEqual(code, 2)
        self.assertIn("config error", err)

    def test_list_command(self) -> None:
        code, out, _ = self.run_cli("list", "-c", str(self.cfg))
        self.assertEqual(code, 0)
        self.assertIn("hello", out)
        self.assertIn("missing 3/3", out)

    def test_list_normalizers(self) -> None:
        code, out, _ = self.run_cli("run", "-c", str(self.cfg), "--list-normalizers")
        self.assertEqual(code, 0)
        self.assertIn("crlf", out)
        self.assertIn("trailing-ws", out)


class DogfoodTests(unittest.TestCase):
    """Integration: snapgate validates its own snapshots."""

    def test_dogfood_run_passes(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
        proc = subprocess.run(
            [PY, "-m", "snapgate", "run"],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("pass", proc.stdout)
        self.assertNotIn("fail", proc.stdout.split("case(s)")[0])


if __name__ == "__main__":
    unittest.main()
