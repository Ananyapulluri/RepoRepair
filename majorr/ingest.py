import ast
import os
import re
import subprocess
import tempfile

GITHUB_RE = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+(\.git)?/?$")
SKIP_DIRS = {".git", "venv", ".venv", "env", "node_modules", "__pycache__", "build", "dist", ".tox"}


def clone_repo(url: str) -> str:
    url = url.strip()
    if not GITHUB_RE.match(url):
        raise ValueError("Please enter a public GitHub URL, e.g. https://github.com/user/repo")
    dest = tempfile.mkdtemp(prefix="rrepo_")
    subprocess.run(["git", "clone", "--depth", "1", url, dest],
                   check=True, capture_output=True, text=True, timeout=300)
    return dest


def python_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if name.endswith(".py"):
                yield os.path.relpath(os.path.join(dirpath, name), root)


def build_chunks(root):
    chunks = []
    for rel in python_files(root):
        with open(os.path.join(root, rel), encoding="utf-8", errors="ignore") as fh:
            src = fh.read()
        lines = src.splitlines()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            chunks.append({"file": rel, "name": "<whole file>", "start": 1,
                           "end": max(len(lines), 1), "code": src})
            continue
        found = False
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                found = True
                start, end = node.lineno, node.end_lineno
                chunks.append({"file": rel, "name": node.name, "start": start, "end": end,
                               "code": "\n".join(lines[start - 1:end])})
        if not found and src.strip():
            chunks.append({"file": rel, "name": "<module>", "start": 1,
                           "end": len(lines), "code": src})
    return chunks