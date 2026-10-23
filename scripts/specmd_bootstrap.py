"""Find a Python 3.11+ interpreter and load SpecMD with its vendored dependencies.

Standard library only and Python 3.8 syntax: the hook command may start with
an old system python3 (macOS ships 3.9). The process is replaced, before stdin
is read, by the first suitable interpreter found.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MINIMUM = (3, 11)
_MARKER = "SPECMD_BOOTSTRAPPED"


def candidates():
    yield os.environ.get("SPECMD_PYTHON")
    for name in ("python3.14", "python3.13", "python3.12", "python3.11", "python3"):
        yield shutil.which(name)
    yield "/opt/homebrew/bin/python3"
    yield "/usr/local/bin/python3"


def suitable(executable, minimum=MINIMUM):
    check = "import sys; sys.exit(0 if sys.version_info[:2] >= %r else 1)" % (tuple(minimum),)
    try:
        return subprocess.run([executable, "-c", check], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def find_interpreter(minimum=MINIMUM):
    current = os.path.realpath(sys.executable)
    for executable in candidates():
        if executable and os.path.isfile(executable) and os.path.realpath(executable) != current \
                and suitable(executable, minimum):
            return executable
    return None


def ensure(script, minimum=MINIMUM):
    """Return True when this interpreter can run SpecMD; otherwise exec a better one or return False."""
    if sys.version_info[:2] >= tuple(minimum):
        sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
        return True
    if os.environ.get(_MARKER):
        return False
    executable = find_interpreter(minimum)
    if executable is None:
        return False
    os.environ[_MARKER] = "1"
    os.execv(executable, [executable, str(script)] + sys.argv[1:])
    return False  # pragma: no cover - execv does not return
