import os

from ingest import SKIP_DIRS


def project_structure(root, max_entries=300):
    lines = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if rel != ".":
            lines.append("  " * (depth - 1) + os.path.basename(dirpath) + "/")
        for name in sorted(filenames):
            if len(lines) >= max_entries:
                return "\n".join(lines) + "\n..."
            lines.append("  " * depth + name)
    return "\n".join(lines)