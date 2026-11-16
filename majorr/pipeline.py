import os

from ingest import clone_repo, build_chunks
from retrieval import CodeIndex
from analysis import run_checks, error_key
from repair import repair_one
from structure import project_structure

MAX_REPAIRS = 5


def run_pipeline(url):
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("The GEMINI_API_KEY environment variable is not set.")

    root = clone_repo(url)
    chunks = build_chunks(root)
    index = CodeIndex(chunks, repo_key=root)
    structure = project_structure(root)

    found, seen = [], set()
    for e in run_checks(root):
        if error_key(e) not in seen:
            seen.add(error_key(e))
            found.append(e)

    repairs = [{"target": t, **repair_one(root, t, index, structure)} for t in found[:MAX_REPAIRS]]

    return {
        "repo": url,
        "root": root,
        "structure": structure,
        "files_analyzed": len({c["file"] for c in chunks}),
        "chunks_indexed": len(chunks),
        "errors_found": found,
        "repairs": repairs,
        "remaining_errors": run_checks(root),
    }