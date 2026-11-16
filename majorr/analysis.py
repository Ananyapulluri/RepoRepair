import ast
import os
import re
import subprocess
import sys

from ingest import python_files

SERIOUS = ("undefined name", "referenced before assignment", "redefinition of unused")
PYFLAKES_LINE = re.compile(r"^(.+?\.py):(\d+):\d+: (.+)$")
PYTEST_LINE = re.compile(r"^(\S+?\.py):(\d+): (.+)$")


def error_key(e):
    return (e["file"], e["message"])


def _rel(root, path):
    if os.path.isabs(path):
        path = os.path.relpath(path, root)
    return os.path.normpath(path)


def syntax_errors(root):
    out = []
    for rel in python_files(root):
        with open(os.path.join(root, rel), encoding="utf-8", errors="ignore") as fh:
            src = fh.read()
        try:
            ast.parse(src)
        except SyntaxError as exc:
            out.append({"kind": "syntax", "file": rel, "line": exc.lineno or 1,
                        "message": f"SyntaxError: {exc.msg}"})
    return out


def pyflakes_errors(root):
    proc = subprocess.run([sys.executable, "-m", "pyflakes", "."], cwd=root,
                          capture_output=True, text=True, timeout=300)
    out = []
    for line in proc.stdout.splitlines():
        m = PYFLAKES_LINE.match(line)
        if m and any(s in m.group(3) for s in SERIOUS):
            out.append({"kind": "static", "file": _rel(root, m.group(1)),
                        "line": int(m.group(2)), "message": m.group(3)})
    return out


def test_errors(root):
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=line",
                           "-p", "no:cacheprovider"],
                          cwd=root, capture_output=True, text=True, timeout=600)
    out = []
    for line in (proc.stdout + proc.stderr).splitlines():
        m = PYTEST_LINE.match(line)
        if m:
            out.append({"kind": "test", "file": _rel(root, m.group(1)),
                        "line": int(m.group(2)), "message": m.group(3).strip()})
    return out


def run_checks(root):
    return syntax_errors(root) + pyflakes_errors(root) + test_errors(root)