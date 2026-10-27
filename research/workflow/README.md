# Local cycle validation

At the root, after `pip install -e .`:

```sh
python scripts/test_local.py
```

The default report goes to `.specmd/local/test-report.json`, rebuildable and without acceptance authority. `--output` lets you save evidence of the run to another path.

The tests use a simulated agent and browser: no LLM is called and no human reading is claimed. They exercise loopback HTTP, Ed25519 decisions, Python/Behave execution in a subprocess, invalidation, failures and resumption through the protocol adapters. The fixtures' keys, receipts and acceptances are created in disposable temporary directories, outside any real contract of the project.

Java and Go have separate validations in [adapters](../../adapters/README.md). Protocol tests do not prove Claude's native dispatch (see [research/claude](../claude/README.md)), human trust through the Codex UX or isolation against another process with the same permissions.

After compiling the example executables, you can reproduce the integration of the real engines with the core:

```sh
python research/workflow/probe_bridges.py \
  --go-executable /path/to/specmd-go-example \
  --java-runner adapters/java/run.sh
```

`evidence/native-bridges.json` records success, assertion failure and undefined step in both languages. `evidence/local-tests.json` records the cycle suite, and `evidence/codex-installation.json` identifies the bundle installed in this stage. None of these files grants acceptance to SpecMD's requirements.

To try the experience yourself, use the [quickstart](../../docs/quickstart.md). The `specmd demo` command creates the proposal and the local demonstration authority, and stops before granting any acceptance.
