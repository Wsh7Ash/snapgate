import tempfile
import unittest
from pathlib import Path

from snapgate.config import ConfigError, load


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


VALID = """
[run]
snapshot_dir = "golden"
timeout = 5

[[case]]
name = "hello"
command = ["python", "-c", "print('hello')"]

[[case]]
name = "echo-args"
command = ["python", "-c", "import sys;print(*sys.argv[1:])"]
matrix = [["one"], ["two"]]

[[normalizer]]
name = "build-id"
pattern = "build-\\\\d+"
replace = "build-<ID>"
"""


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_load_valid(self) -> None:
        cfg = load(write(self.dir / "snapgate.toml", VALID))
        self.assertEqual(cfg.snapshot_dir, "golden")
        self.assertEqual([c.name for c in cfg.cases], ["hello", "echo-args[0]", "echo-args[1]"])
        self.assertEqual(cfg.cases[1].command[-1], "one")
        self.assertEqual(cfg.cases[0].timeout, 5.0)
        self.assertEqual(len(cfg.normalizers), 1)
        self.assertEqual(cfg.snapshot_root, self.dir / "golden")

    def test_matrix_appends_to_shared_command(self) -> None:
        cfg = load(write(self.dir / "snapgate.toml", VALID))
        echo = next(c for c in cfg.cases if c.name == "echo-args[1]")
        self.assertEqual(echo.command[1:3], ["-c", "import sys;print(*sys.argv[1:])"])
        self.assertEqual(echo.command[3], "two")

    def test_missing_file(self) -> None:
        with self.assertRaises(ConfigError):
            load(self.dir / "nope.toml")

    def test_unknown_top_level_key(self) -> None:
        path = write(self.dir / "snapgate.toml", 'wat = 1\n[[case]]\nname="a"\ncommand=["python"]\n')
        with self.assertRaisesRegex(ConfigError, "unknown key"):
            load(path)

    def test_unknown_case_key(self) -> None:
        path = write(self.dir / "snapgate.toml", '[[case]]\nname="a"\ncommand=["python"]\nbogus=1\n')
        with self.assertRaisesRegex(ConfigError, "unknown key"):
            load(path)

    def test_no_cases(self) -> None:
        path = write(self.dir / "snapgate.toml", "[run]\ntimeout = 3\n")
        with self.assertRaisesRegex(ConfigError, "no cases"):
            load(path)

    def test_case_without_command(self) -> None:
        path = write(self.dir / "snapgate.toml", '[[case]]\nname="a"\n')
        with self.assertRaisesRegex(ConfigError, "command"):
            load(path)

    def test_duplicate_names(self) -> None:
        path = write(
            self.dir / "snapgate.toml",
            '[[case]]\nname="a"\ncommand=["python"]\n[[case]]\nname="a"\ncommand=["python"]\n',
        )
        with self.assertRaisesRegex(ConfigError, "duplicate"):
            load(path)

    def test_bad_timeout(self) -> None:
        path = write(
            self.dir / "snapgate.toml",
            '[[case]]\nname="a"\ncommand=["python"]\ntimeout=-1\n',
        )
        with self.assertRaisesRegex(ConfigError, "timeout"):
            load(path)

    def test_invalid_toml(self) -> None:
        path = write(self.dir / "snapgate.toml", "[run\nbroken")
        with self.assertRaisesRegex(ConfigError, "invalid TOML"):
            load(path)


if __name__ == "__main__":
    unittest.main()
