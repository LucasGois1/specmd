import unittest

from specmd.config import ConfigError, parse_config


class ConfigTests(unittest.TestCase):
    def test_every_key_is_optional(self):
        self.assertEqual(parse_config(b""), {})

    def test_supported_options(self):
        config = parse_config(b'''
gherkin_language = "pt"
wip_tags = ["wip", "pendente"]

[run]
on_stop = false
timeout = 90

[[runners]]
id = "python"
language = "python"
steps = "features/steps"
python = ".venv/bin/python"
paths = ["docs/**"]

[[runners]]
id = "go"
language = "go"
command = ["./bin/bridge", "", " arg "]
''')
        self.assertEqual(config["wip_tags"], ["wip", "pendente"])
        self.assertFalse(config["run"]["on_stop"])
        self.assertEqual(config["runners"][1]["command"], ["./bin/bridge", "", " arg "])

    def test_legacy_keys_from_the_audit_design_are_ignored(self):
        config = parse_config(b'schema = 2\nproject_id = "x"\n[traceability]\npolicy = "strict"\n[evidence]\nallow_mock = false\n')
        self.assertEqual(config["schema"], 2)

    def test_invalid_values_are_rejected(self):
        for content in (
            b"schema = 3\n", b"schema = true\n", b"unknown = 1\n", b"gherkin_language = 1\n",
            b"wip_tags = \"wip\"\n", b"wip_tags = [1]\n", b"[run]\non_stop = \"sim\"\n", b"[run]\ntimeout = 0\n",
            b"[run]\nextra = 1\n", b"runners = {}\n", b"[[runners]]\nlanguage = \"python\"\n",
            b"[[runners]]\nid = \"p\"\nlanguage = \"python\"\ncommand = []\n",
            b"[[runners]]\nid = \"p\"\nlanguage = \"python\"\ntimeout = -1\n",
            b"[[runners]]\nid = \"p\"\nlanguage = \"python\"\npython = \"\"\n",
            b"[[runners]]\nid = \"p\"\nlanguage = \"python\"\n[[runners]]\nid = \"p\"\nlanguage = \"go\"\n",
            b"x = [\n", "ç".encode("latin-1"),
        ):
            with self.subTest(content=content), self.assertRaises(ConfigError):
                parse_config(content)


if __name__ == "__main__":
    unittest.main()
