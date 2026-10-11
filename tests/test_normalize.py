import unittest

from snapgate.normalize import Normalizer, apply, builtins


class BuiltinNormalizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chain = builtins()

    def norm(self, name: str, text: str) -> str:
        for n in self.chain:
            if n.name == name:
                return apply(text, [n])
        raise AssertionError(f"no builtin normalizer named {name}")

    def test_crlf(self) -> None:
        self.assertEqual(self.norm("crlf", "a\r\nb\r\n"), "a\nb\n")

    def test_iso_timestamp(self) -> None:
        self.assertEqual(self.norm("iso-timestamp", "at 2026-10-10T12:34:56Z done"), "at <TIMESTAMP> done")
        self.assertEqual(self.norm("iso-timestamp", "2026-10-10 12:34:56.789+02:00"), "<TIMESTAMP>")

    def test_epoch(self) -> None:
        self.assertEqual(self.norm("epoch", "ts=1791648000"), "ts=<EPOCH>")
        self.assertEqual(self.norm("epoch", "1791648000123 ms"), "<EPOCH> ms")
        self.assertEqual(self.norm("epoch", "year 2026 ok"), "year 2026 ok")

    def test_uuid(self) -> None:
        self.assertEqual(
            self.norm("uuid", "id=550e8400-e29b-41d4-a716-446655440000"),
            "id=<UUID>",
        )

    def test_duration(self) -> None:
        self.assertEqual(self.norm("duration", "took 123ms"), "took <DUR>")
        self.assertEqual(self.norm("duration", "took 1.25s"), "took <DUR>")
        self.assertEqual(self.norm("duration", "took 42ns"), "took <DUR>")

    def test_hex_hash(self) -> None:
        self.assertEqual(
            self.norm("hex-hash", "sha=deadbeefcafebabe"),
            "sha=<HASH>",
        )
        self.assertEqual(self.norm("hex-hash", "beef"), "beef")

    def test_path_windows_and_posix(self) -> None:
        self.assertEqual(self.norm("path", "f=C:\\Users\\demo\\tmp\\out.txt"), "f=<PATH>")
        self.assertEqual(self.norm("path", "f=/tmp/work/dir/file.log"), "f=<PATH>")

    def test_trailing_whitespace(self) -> None:
        self.assertEqual(self.norm("trailing-ws", "line1   \nline2\t\n"), "line1\nline2\n")

    def test_chain_is_idempotent(self) -> None:
        sample = "at 2026-10-10T12:34:56Z id=550e8400-e29b-41d4-a716-446655440000 took 12ms  "
        once = apply(sample, self.chain)
        twice = apply(once, self.chain)
        self.assertEqual(once, twice)
        self.assertNotEqual(sample, once)

    def test_custom_normalizer(self) -> None:
        custom = Normalizer("version", r"v\d+\.\d+\.\d+", "v<X>")
        self.assertEqual(apply("released v1.2.3 today", [custom]), "released v<X> today")


if __name__ == "__main__":
    unittest.main()
