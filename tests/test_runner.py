import sys
import tempfile
import unittest
from pathlib import Path

from snapgate.config import Case, Config, load
from snapgate.runner import check_case, execute, ordered_normalizers, snapshot_files

PY = sys.executable.replace("\\", "/")

CONFIG = """
[run]
snapshot_dir = "snapshots"
command = ["%(py)s", "-c", "print('default')"]

[[case]]
name = "stdin-upper"
command = ["%(py)s", "-c", "import sys;print(sys.stdin.read().upper())"]
stdin = "abc\\n"

[[case]]
name = "env-probe"
command = ["%(py)s", "-c", "import os;print(os.environ['SNAPGATE_PROBE'])"]

[[case]]
name = "cwd-probe"
command = ["%(py)s", "-c", "import os;print(os.path.basename(os.getcwd()))"]
cwd = "sub"

[[case]]
name = "slow"
command = ["%(py)s", "-c", "import time;time.sleep(3)"]
timeout = 0.3

[[case]]
name = "missing-bin"
command = ["definitely-not-a-real-binary-xyz"]
""" % {"py": PY}


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        (self.dir / "sub").mkdir()
        self.config = load(write_cfg(self.dir, CONFIG))

    def case(self, name: str) -> Case:
        return next(c for c in self.config.cases if c.name == name)

    def test_execute_captures_output(self) -> None:
        result = execute(self.case("stdin-upper"), self.config)
        self.assertEqual(result.stdout, "ABC\n\n")
        self.assertEqual(result.exit_code, 0)
        self.assertFalse(result.timed_out)

    def test_env_and_cwd_overrides(self) -> None:
        import os

        self.config.cases = [c for c in self.config.cases if c.name in {"env-probe", "cwd-probe"}]
        env_case = self.case("env-probe")
        env_case.env = {"SNAPGATE_PROBE": "probe-value"}
        self.assertEqual(execute(env_case, self.config).stdout, "probe-value\n")
        self.assertEqual(execute(self.case("cwd-probe"), self.config).stdout, "sub\n")

    def test_pass_after_update(self) -> None:
        case = self.case("stdin-upper")
        first = check_case(case, self.config)
        self.assertEqual(first.status, "missing")
        second = check_case(case, self.config, update=True)
        self.assertEqual(second.status, "created")
        third = check_case(case, self.config)
        self.assertEqual(third.status, "pass")

    def test_fail_on_changed_output(self) -> None:
        case = self.case("stdin-upper")
        check_case(case, self.config, update=True)
        case.stdin = "xyz\n"
        result = check_case(case, self.config)
        self.assertEqual(result.status, "fail")
        self.assertTrue(result.diffs)
        self.assertIn("-ABC", result.diffs[0])
        self.assertIn("+XYZ", result.diffs[0])

    def test_timeout_is_reported_not_hung(self) -> None:
        result = check_case(self.case("slow"), self.config)
        self.assertEqual(result.status, "timeout")
        self.assertIn("timed out", result.reason)

    def test_command_not_found(self) -> None:
        result = check_case(self.case("missing-bin"), self.config)
        self.assertEqual(result.status, "error")
        self.assertIn("command not found", result.reason)

    def test_snapshot_paths(self) -> None:
        files = snapshot_files(self.case("stdin-upper"), self.config)
        self.assertEqual(files["stdout"].name, "stdout.txt")
        self.assertEqual(files["stdout"].parts[-3:], ("snapshots", "stdin-upper", "stdout.txt"))

    def test_normalizer_order_builtins_then_custom(self) -> None:
        names = [n.name for n in ordered_normalizers(self.config)]
        self.assertEqual(names[0], "crlf")
        self.assertEqual(names[-1], "trailing-ws")
        self.assertEqual(names[3], "pid")
        self.assertEqual(len(names), 9)

    def test_update_is_idempotent(self) -> None:
        case = self.case("stdin-upper")
        check_case(case, self.config, update=True)
        again = check_case(case, self.config, update=True)
        self.assertEqual(again.status, "unchanged")


def write_cfg(directory: Path, text: str) -> Path:
    path = directory / "snapgate.toml"
    path.write_text(text, encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
